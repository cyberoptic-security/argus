from app.sources.alienvault import AlienVaultSource
from app.sources.anubisdb import AnubisDBSource
from app.sources.base import Source
from app.sources.bufferover import BufferOverSource
from app.sources.censys import CensysSource
from app.sources.chaos import ChaosSource
from app.sources.crtsh import CrtShSource
from app.sources.fullhunt import FullHuntSource
from app.sources.hackertarget import HackerTargetSource
from app.sources.leakix import LeakIXSource
from app.sources.netlas import NetlasSource
from app.sources.securitytrails import SecurityTrailsSource
from app.sources.shodan import ShodanSource
from app.sources.threatcrowd import ThreatCrowdSource
from app.sources.urlscan import UrlScanSource
from app.sources.virustotal import VirusTotalSource

_all_sources: list[Source] = [
    CrtShSource(),
    HackerTargetSource(),
    AlienVaultSource(),
    BufferOverSource(),
    AnubisDBSource(),
    ThreatCrowdSource(),
    UrlScanSource(),
    VirusTotalSource(),
    ShodanSource(),
    CensysSource(),
    SecurityTrailsSource(),
    ChaosSource(),
    NetlasSource(),
    LeakIXSource(),
    FullHuntSource(),
]

SOURCES: dict[str, Source] = {src.name: src for src in _all_sources}
