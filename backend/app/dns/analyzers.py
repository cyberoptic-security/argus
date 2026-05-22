from dataclasses import dataclass

DKIM_COMMON_SELECTORS = [
    "google", "mail", "default", "dkim", "selector1", "selector2",
    "k1", "s1", "s2", "proofpoint", "mimecast", "mandrill",
    "sendgrid", "mailchimp", "amazonses", "smtp", "email", "pm",
    "fm1", "fm2",
]


@dataclass
class Finding:
    fqdn: str
    check_type: str   # spf | dmarc | mx | dkim
    status: str       # pass | warn | fail | info
    severity: str     # critical | high | medium | low | info
    title: str
    detail: str
    raw_value: str | None = None
    recommendation: str | None = None


# ── SPF ───────────────────────────────────────────────────────────────────────

def _spf_all_qualifier(record: str) -> str | None:
    for tok in record.split():
        t = tok.lower()
        if t in ("-all", "~all", "?all", "+all"):
            return t
        if t == "all":
            return "+all"  # bare 'all' with no qualifier = implicit pass
    return None


def _spf_include_count(record: str) -> int:
    return sum(1 for t in record.split() if t.lower().startswith("include:"))


def analyze_spf(fqdn: str, txt_records: list[str], has_mx: bool) -> list[Finding]:
    spf = [r for r in txt_records if r.strip().lower().startswith("v=spf1")]

    if not spf:
        if has_mx:
            return [Finding(
                fqdn=fqdn, check_type="spf", status="fail", severity="critical",
                title="No SPF record — domain has mail servers",
                detail=(
                    "This domain has MX records but no SPF record. Any mail server on the "
                    "internet can send email claiming to be from this domain, and receiving "
                    "servers have no SPF-based way to detect or reject it."
                ),
                recommendation=f"Add a TXT record at {fqdn}: v=spf1 include:_spf.yourprovider.com -all",
            )]
        return [Finding(
            fqdn=fqdn, check_type="spf", status="warn", severity="medium",
            title="No SPF record",
            detail=(
                "No SPF record found. This domain has no MX records, but email can still be "
                "spoofed in the From: header without SPF. DMARC also loses one authentication path."
            ),
            recommendation=f"Add: v=spf1 -all at {fqdn} to declare this domain sends no email.",
        )]

    if len(spf) > 1:
        return [Finding(
            fqdn=fqdn, check_type="spf", status="fail", severity="critical",
            title=f"Multiple SPF records ({len(spf)}) — invalid per RFC 7208",
            detail=(
                "RFC 7208 requires exactly one SPF TXT record. When multiple exist, receivers "
                "MUST return a PermError and treat SPF as failed, negating all SPF protection."
            ),
            raw_value="\n".join(spf),
            recommendation="Merge all mechanisms into a single SPF record.",
        )]

    record = spf[0]
    findings: list[Finding] = []
    qualifier = _spf_all_qualifier(record)
    include_count = _spf_include_count(record)

    if include_count > 8:
        findings.append(Finding(
            fqdn=fqdn, check_type="spf", status="warn", severity="medium",
            title=f"SPF nearing 10 DNS lookup limit (~{include_count} includes)",
            detail=(
                "SPF evaluation is limited to 10 DNS lookups (RFC 7208 §4.6.4). Exceeding this "
                "causes a PermError, which many receivers treat as a hard fail — breaking mail delivery."
            ),
            raw_value=record,
            recommendation="Use SPF record flattening or reduce the number of include: mechanisms.",
        ))

    if qualifier is None:
        findings.append(Finding(
            fqdn=fqdn, check_type="spf", status="warn", severity="medium",
            title="SPF record missing default 'all' policy",
            detail=(
                "Without an 'all' mechanism, receivers have no instruction for hosts not listed "
                "in the record. Behavior becomes undefined and spoofing protection is incomplete."
            ),
            raw_value=record,
            recommendation="Append -all (hard fail) or ~all (softfail) to the record.",
        ))
    elif qualifier == "+all":
        findings.append(Finding(
            fqdn=fqdn, check_type="spf", status="fail", severity="critical",
            title="SPF +all — any server can spoof this domain",
            detail=(
                "+all authorises every mail server on the internet to send as this domain. "
                "This completely defeats SPF and is one of the worst possible configurations."
            ),
            raw_value=record,
            recommendation="Replace +all with -all immediately. Use ~all as a safe transitional step.",
        ))
    elif qualifier == "?all":
        findings.append(Finding(
            fqdn=fqdn, check_type="spf", status="fail", severity="high",
            title="SPF neutral policy (?all) — no enforcement",
            detail=(
                "?all instructs receivers not to use SPF to accept or reject mail. The record "
                "exists but provides zero enforcement, making it functionally equivalent to no SPF."
            ),
            raw_value=record,
            recommendation="Change ?all to -all or ~all.",
        ))
    elif qualifier == "~all":
        findings.append(Finding(
            fqdn=fqdn, check_type="spf", status="warn", severity="medium",
            title="SPF soft-fail (~all) — partial protection",
            detail=(
                "~all asks receivers to accept but mark unauthorised senders. Most receivers "
                "deliver to spam rather than reject. Common during rollout; not the final goal."
            ),
            raw_value=record,
            recommendation="Harden to -all once all legitimate sending sources are confirmed.",
        ))
    else:  # -all
        non_all = [t for t in record.split() if t.lower() not in ("v=spf1", "-all")]
        if not non_all:
            findings.append(Finding(
                fqdn=fqdn, check_type="spf", status="pass", severity="info",
                title="SPF rejects all senders — non-sending domain (optimal)",
                detail="v=spf1 -all correctly declares this domain sends no email. Spoofed messages hard-fail SPF.",
                raw_value=record,
            ))
        else:
            findings.append(Finding(
                fqdn=fqdn, check_type="spf", status="pass", severity="info",
                title="SPF hard-fail (-all) — correctly configured",
                detail="SPF uses -all: unlisted senders are hard-rejected. This is the strongest SPF enforcement.",
                raw_value=record,
            ))

    return findings


# ── DMARC ─────────────────────────────────────────────────────────────────────

def _parse_dmarc(record: str) -> dict[str, str]:
    tags: dict[str, str] = {}
    for part in record.split(";"):
        part = part.strip()
        if "=" in part:
            k, _, v = part.partition("=")
            tags[k.strip().lower()] = v.strip()
    return tags


def analyze_dmarc(
    fqdn: str,
    own_records: list[str],
    root_domain: str,
    root_records: list[str],
    is_root: bool,
) -> list[Finding]:
    own = next((r for r in own_records if "v=dmarc1" in r.lower()), None)
    root = next((r for r in root_records if "v=dmarc1" in r.lower()), None) if not is_root else None

    if not own:
        if is_root:
            return [Finding(
                fqdn=fqdn, check_type="dmarc", status="fail", severity="high",
                title="No DMARC policy",
                detail=(
                    f"No DMARC record at _dmarc.{fqdn}. Without DMARC, SPF and DKIM results "
                    "are not enforced end-to-end, leaving the domain vulnerable to From: header "
                    "spoofing (Business Email Compromise attacks)."
                ),
                recommendation=(
                    f"Create a TXT record at _dmarc.{fqdn}: "
                    f"v=DMARC1; p=none; rua=mailto:dmarc@{fqdn}  — then move to p=quarantine "
                    "and ultimately p=reject."
                ),
            )]

        if root:
            tags = _parse_dmarc(root)
            rp = tags.get("p", "none")
            sp = tags.get("sp", rp)  # sp defaults to p when unset
            if sp == "reject":
                return [Finding(
                    fqdn=fqdn, check_type="dmarc", status="pass", severity="info",
                    title=f"Protected by root domain DMARC (effective sp=reject)",
                    detail=(
                        f"No DMARC at _dmarc.{fqdn}, but {root_domain} has DMARC with "
                        f"p={rp} and effective subdomain policy sp=reject. "
                        "Subdomains inherit this rejection-level protection."
                    ),
                    raw_value=root,
                )]
            if sp == "quarantine":
                return [Finding(
                    fqdn=fqdn, check_type="dmarc", status="warn", severity="low",
                    title=f"Inherits root DMARC quarantine policy (effective sp=quarantine)",
                    detail=(
                        f"Spoofed mail from this subdomain will be quarantined (spam folder) "
                        f"but not rejected outright. Root domain: {root_domain} (p={rp})."
                    ),
                    raw_value=root,
                    recommendation=f"Set sp=reject in _dmarc.{root_domain} for full subdomain protection.",
                )]
            # sp=none
            return [Finding(
                fqdn=fqdn, check_type="dmarc", status="fail", severity="high",
                title="Root DMARC has no subdomain enforcement (effective sp=none)",
                detail=(
                    f"Root domain {root_domain} has DMARC with p={rp}, but the effective "
                    "subdomain policy is sp=none (monitoring only). This subdomain is NOT protected."
                ),
                raw_value=root,
                recommendation=f"Remove sp=none or set sp=reject in _dmarc.{root_domain}.",
            )]

        return [Finding(
            fqdn=fqdn, check_type="dmarc", status="fail", severity="high",
            title="No DMARC on subdomain or root domain",
            detail=(
                f"Neither _dmarc.{fqdn} nor _dmarc.{root_domain} has a DMARC record. "
                "There is no DMARC protection anywhere in this domain hierarchy."
            ),
            recommendation=(
                f"Add DMARC at _dmarc.{root_domain} with sp=reject to protect "
                "all subdomains at once."
            ),
        )]

    # Has own DMARC record
    tags = _parse_dmarc(own)
    policy = tags.get("p", "none")
    try:
        pct = int(tags.get("pct", "100"))
    except ValueError:
        pct = 100
    has_rua = bool(tags.get("rua"))
    sp = tags.get("sp")

    findings: list[Finding] = []

    if policy == "none":
        findings.append(Finding(
            fqdn=fqdn, check_type="dmarc", status="warn", severity="medium",
            title="DMARC in monitoring mode only (p=none)",
            detail=(
                "p=none sends reports but does NOT enforce policy. Spoofed email is still "
                "delivered. Appropriate only as a temporary diagnostic state — not for production."
            ),
            raw_value=own,
            recommendation="Review rua aggregate reports, then move to p=quarantine and ultimately p=reject.",
        ))
    elif policy == "quarantine":
        findings.append(Finding(
            fqdn=fqdn, check_type="dmarc", status="warn", severity="low",
            title="DMARC quarantine policy (p=quarantine)",
            detail=(
                "Failing messages are sent to spam/junk. Provides partial protection — "
                "spoofed mail still reaches recipients via the spam folder."
            ),
            raw_value=own,
            recommendation="Move to p=reject when confident all legitimate mail passes DMARC.",
        ))
    elif policy == "reject":
        findings.append(Finding(
            fqdn=fqdn, check_type="dmarc", status="pass", severity="info",
            title="DMARC reject policy (p=reject) — strongest protection",
            detail=(
                "Emails failing DMARC are rejected at the receiving MTA. "
                "This is the gold standard for preventing domain spoofing."
            ),
            raw_value=own,
        ))

    if pct < 100:
        findings.append(Finding(
            fqdn=fqdn, check_type="dmarc", status="warn", severity="medium",
            title=f"DMARC applies to only {pct}% of messages (pct={pct})",
            detail=(
                f"The remaining {100 - pct}% bypass DMARC enforcement entirely. "
                "Often used during rollout — should be 100 in production."
            ),
            raw_value=own,
            recommendation="Set pct=100 once all legitimate senders consistently pass DMARC.",
        ))

    if not has_rua:
        findings.append(Finding(
            fqdn=fqdn, check_type="dmarc", status="warn", severity="low",
            title="No DMARC aggregate reporting configured (rua missing)",
            detail=(
                "Without rua=, you receive no reports about who is sending as your domain. "
                "These reports are critical for detecting spoofing and finding misconfigured senders."
            ),
            raw_value=own,
            recommendation="Add rua=mailto:dmarc-reports@yourdomain.com or use a DMARC reporting service.",
        ))

    # Warn when root domain subdomain policy is weaker than root policy
    if is_root and sp is not None:
        if sp == "none" and policy in ("quarantine", "reject"):
            findings.append(Finding(
                fqdn=fqdn, check_type="dmarc", status="warn", severity="medium",
                title=f"Subdomain policy weaker than root (sp=none, p={policy})",
                detail=(
                    f"Root domain protected at p={policy}, but all subdomains are in "
                    "monitoring-only mode (sp=none) — they can be spoofed freely."
                ),
                raw_value=own,
                recommendation=f"Set sp={policy} or remove sp= to inherit the root policy.",
            ))
        elif sp == "quarantine" and policy == "reject":
            findings.append(Finding(
                fqdn=fqdn, check_type="dmarc", status="warn", severity="low",
                title="Subdomain policy weaker than root (sp=quarantine, p=reject)",
                detail=(
                    "Subdomains use quarantine while the root uses reject. "
                    "Subdomain spoofed mail lands in spam rather than being rejected."
                ),
                raw_value=own,
                recommendation="Set sp=reject for consistent subdomain enforcement.",
            ))

    return findings


# ── MX ────────────────────────────────────────────────────────────────────────

def analyze_mx(fqdn: str, mx_records: list[tuple[int, str]]) -> list[Finding]:
    if not mx_records:
        return [Finding(
            fqdn=fqdn, check_type="mx", status="info", severity="info",
            title="No MX records — domain does not receive email",
            detail="No mail exchange servers are configured. This domain cannot receive email directly.",
        )]
    mx_str = ", ".join(f"{h} (pri {p})" for p, h in mx_records[:5])
    extra = f" (+{len(mx_records) - 5} more)" if len(mx_records) > 5 else ""
    return [Finding(
        fqdn=fqdn, check_type="mx", status="info", severity="info",
        title=f"{len(mx_records)} MX record{'s' if len(mx_records) != 1 else ''} — receives email",
        detail=f"Mail servers: {mx_str}{extra}",
    )]


# ── DKIM ──────────────────────────────────────────────────────────────────────

def analyze_dkim(fqdn: str, found: list[str]) -> list[Finding]:
    if found:
        return [Finding(
            fqdn=fqdn, check_type="dkim", status="pass", severity="info",
            title=f"DKIM key{'s' if len(found) != 1 else ''} found ({len(found)} selector{'s' if len(found) != 1 else ''})",
            detail=f"Active DKIM selectors found at common names: {', '.join(found)}",
        )]
    return [Finding(
        fqdn=fqdn, check_type="dkim", status="warn", severity="low",
        title="No DKIM found at common selector names",
        detail=(
            "No DKIM public keys were found at common selector names (google, mail, default, "
            "selector1, selector2, etc.). This is NOT conclusive — DKIM selectors are arbitrary "
            "strings chosen by your mail provider."
        ),
        recommendation=(
            "Check your email provider's documentation for the correct DKIM selector name "
            "and verify the DNS TXT record exists at {selector}._domainkey." + fqdn
        ),
    )]
