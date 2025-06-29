"""
projekt_3.py: Třetí projekt do Engeto Online Python Akademie
autor: Lenka Krčmáriková
email: l.krcmarikova@seznam.cz
discord: lenka_34840
"""

# Standardní knihovny
import csv
import json
import logging
import os
import sys
import time
import xml.etree.ElementTree as ET
from logging.handlers import RotatingFileHandler
from typing import List, TypedDict

# Knihovny třetích stran
from bs4 import BeautifulSoup
import requests
from requests.exceptions import RequestException, Timeout
from tqdm import tqdm
from colorama import Fore, init

# Inicializace colorama
init(autoreset=True)

BASE_URL = "https://www.volby.cz/pls/ps2017nss/"

SEPARATOR = "=" * 79

class Okrsek(TypedDict):
    url: str
    cislo_obce: str
    nazev_obce: str

class Strana(TypedDict):
    strana: str
    hlasy: int

class ObecData(TypedDict):
    obec: str
    volici: int
    vydane_obalky: int
    platne_hlasy: int
    strany: List[Strana]

# Definování vlastních výjimek
class ValidationError(Exception):
    """Vlastní výjimka pro chyby validace."""
    pass

class NoDataFoundError(Exception):
    """
    Vlastní výjimka pro případ, kdy nejsou nalezena žádná data.
    """
    pass

class DataParsingError(Exception):
    """
    Vlastní výjimka pro chyby při parsování dat.
    """
    pass

class FileSavingError(Exception):
    """
    Vlastní výjimka pro chyby při ukládání.
    """
    pass

class UnsupportedFormatError(Exception):
    """
    Vlastní výjimka pro chyby při zadávání typu formátu souboru.
    """
    pass

# Zprávy pro uživatele
MSG_CRITICAL = """
    🚨 KRITICKÁ NEOČEKÁVANÁ CHYBA:
    Během zpracování dat nastala kritická a neočekávaná chyba: 
    {error_detail}
    Program bude ukončen. 
    Prosím, zkontroluj log soubor pro detailní informace.
"""

MSG_ERROR_ARGUMENTS_COUNT = """
    ❌ CHYBA PŘI SPUŠTĚNÍ:
    Očekávám dva argumenty: URL okresu a název výstupního souboru.
    
    Správné použití:
    python {script_name} <URL_okresu> <vystupni_soubor.csv/json/xml>
    
    Příklad:
    python volby_scraper.py "https://www.volby.cz/..." "vysledky.csv"
"""
MSG_ERROR_REQUEST_FAILED = """
    ❌ CHYBA PŘI ZÍSKÁVÁNÍ SEZNAMU OBCÍ:
    Nepodařilo se stáhnout data ze stránky: {url}
    Detail chyby: {error_detail}
    
    Zkontroluj prosím své připojení k internetu a zadanou URL.
"""
MSG_ERROR_SAVE_FAILED = """
    ❌ CHYBA PŘI UKLÁDÁNÍ SOUBORU '{filename}':
    Nepodařilo se uložit data do souboru.
    Detail chyby: {error_detail}
    
    Zkontroluj prosím, zda máš oprávnění k zápisu do cílového umístění a
    zda soubor není používán jiným programem.
"""
MSG_ERROR_UNEXPECTED = """
    ❌ NEOČEKÁVANÁ CHYBA:
    Při {operation} nastala neočekávaná chyba: {error_detail}
    Kontaktuj prosím vývojáře s log souborem pro detailní informace.
"""
MSG_ERROR_UNSUPPORTED_FORMAT = """
    ❌ Nepodporovaný formát souboru: {format_typ}. Zkontroluj příponu.
    Podporované formáty: 📋.csv, 📝.json, 🔤.xml
"""
MSG_ERROR_URL_VALIDATION = """
    ❌ CHYBA PŘI VALIDACI URL:
    Zadaná URL '{url}' není platná.
    Detail chyby: {error_detail}
    
    Ujisti se, že URL začíná
        -> 'http://' nebo 'https://',
        -> obsahuje 'volby.cz' a
        -> je správná pro dané volby.
"""

MSG_INFO_COUNT_OBCE = "    🔄 Celkový počet obcí ke zpracování: {total}"
MSG_INFO_GETTING_LIST = "    📋 Získávám seznam obcí z adresy..."
MSG_INFO_PROCESSING_DATA = """    
    🔄 Zpracovávám volební data pro jednotlivé obce..."""
MSG_INFO_PROCESSING_OBCE = """
Zpracovávám obec {cislo}/{total}: {obec_nazev} (Číslo: {obec_cislo})
"""
MSG_INFO_SAVING = """
    💾 Ukládám výsledky do souboru '{filename}' ve formátu {format}...
"""
MSG_INFO_SUCCESS_SAVE = """
    ✅ HOTOVO! Výsledky byly úspěšně uloženy do '{filename}'.
"""
MSG_INFO_VALIDATION = "    🔍 Probíhá validace URL: {url}"

MSG_STATISTICS = """
    📊 Souhrn zpracování:
       ------------------
       Doba zpracování: {time}
       Zpracováno obcí: {pocet}
       Počet chyb: {chyby}
       Celkový počet voličů: {volici:,}
       Celkový počet platných hlasů: {hlasy:,}
       Průměrná volební účast: {ucast:.2f}%
"""

MSG_WARNING_NO_DATA_FOUND = """
    ⚠️ VAROVÁNÍ: Nebyly nalezeny žádné obce ke zpracování!
    Zkontroluj prosím zadanou URL adresu: {url}
"""
MSG_WARNING_NO_DATA_SAVE = """
    ⚠️ VAROVÁNÍ:
    Nebyla nalezena žádná data k uložení. Soubor nebude vytvořen.
"""
MSG_WARNING_PROCESSING_ERROR = """
    ⚠️ VAROVÁNÍ:
    Chyba při stahování dat pro obec '{obec_nazev}' ({obec_cislo}).
    Tato obec bude přeskočena.
    Detail chyby: {error_detail}
"""

# Log zprávy
LOG_CRITICAL = "Kritická neočekávaná chyba během hlavního procesu: {error_detail}"
LOG_CRITICAL_UNEXPECTED = """
Kritická neočekávaná chyba během hlavního procesu při {operation}: {error_detail}
"""

LOG_DEBUG_LOADED_DATA = "Načtená strana '{strana}', hlasy: '{hlasy}'"
LOG_DEBUG_PROCESSING_OBCE = """
Zpracovávám obec:
        {obec_nazev}
        ({obec_cislo})
        z URL: {url}
"""
LOG_DEBUG_OBCE_PROCESSED = """
Data pro obec {obec_nazev} ({obec_cislo}) úspěšně zpracována.
"""
LOG_DEBUG_SKIP_ROW = "Přeskakuji nevalidní řádek: '{strana}' – '{hlasy}'"

LOG_ERROR_ARGUMENTS_COUNT = "Nesprávný počet argumentů."
LOG_ERROR_BEGIN = "URL musí začínat 'http://' nebo 'https://'"
LOG_ERROR_DATA_FAILED = """
Zpracování dat selhalo kvůli nenalezeným obcím: {error_detail}"""
LOG_ERROR_DOMENA = "URL musí být z domény volby.cz"
LOG_ERROR_GETTING_LIST = "Chyba při získávání seznamu obcí: {error_detail}"
LOG_ERROR_NO_DATA_FOUND = """
Varování: Nebyl nalezen žádný odkaz na obce na adrese '{url}'.
"""
LOG_ERROR_PARSING_DATA = "Chyba v datech pro danou obec: {error_detail}"
LOG_ERROR_PARSING_ERROR = """
Chyba při parsování dat pro obec {obec_nazev} ({obec_cislo}): {error_detail}
"""
LOG_ERROR_ROK = "URL musí obsahovat rok voleb: {rok}"
LOG_ERROR_REQUEST = "Chyba při {operation}: {error_detail}"
LOG_ERROR_REQUEST_FAILED = """
Chyba při stahování dat z URL '{url}': {error_detail}
"""
LOG_ERROR_REQUEST_OBCE_FAILED = """
Chyba při stahování dat pro obec {obec_nazev} ({obec_cislo}): {error_detail}
"""
LOG_ERROR_SAVE_FAILED = "Chyba při ukládání souboru '{filename}': {error_detail}"
LOG_ERROR_SAVING_FAILED = "Ukládání selhalo kvůli nenalezeným datům."
LOG_ERROR_TIME_OUT = "Vypršel časový limit při {operation}: {error_detail}"
LOG_ERROR_UNEXPECTED = "Neočekávaná chyba při {operation}: {error_detail}"
LOG_ERROR_UNEXPECTED_OBCE = """
Neočekávaná chyba při zpracování obce {obec_nazev} 
({obec_cislo}): {error_detail}
"""
LOG_ERROR_UNEXPECTED_SAVE = """
Neočekávaná chyba při ukládání souboru '{filename}': {error_detail}"""
LOG_ERROR_UNSUPPORTED_FORMAT = """
Nepodporovaný formát souboru: {format_typ}"""
LOG_ERROR_UNSUPPORTED_FORMAT_FAILED = """
Ukládání souboru selhalo kvůli nepodporovaném formátu souboru {error_detail}.
"""
LOG_ERROR_URL_VALIDATION = "Neplatná URL '{url}': {error_detail} "

LOG_INFO_COUNT_OBCE = "Úspěšně získán seznam {count} obcí."
LOG_INFO_GETTING_OBCE = "Zahajuji získávání seznamu obcí z URL: {url}"
LOG_INFO_OBCE_PROCESSED = "Zpracování dat pro obce dokončeno."
LOG_INFO_PROCESSING_OBCE = "Zahajuji zpracování dat pro jednotlivé obce."
LOG_INFO_PROCESSING_FINISHED = "Zpracování dat pro obce dokončeno."
LOG_INFO_PROGRAM_EXIT = """
Program bude ukončen s kódem {exit_code} kvůli kritické chybě.
"""
LOG_INFO_SAVE_SUCCESS = "Výsledky úspěšně uloženy do souboru '{filename}'."
LOG_INFO_SAVING = """
Zahahuji ukládání výsledků do souboru '{filename}' ve formátu {format}.
"""
LOG_INFO_URL_VALIDATED = "URL '{url}' úspěšně validována."

LOG_RAISE_NO_DATA_FOUND = """
Na adrese '{url}' nebyly nalezeny žádné odkazy na obce."""

LOG_WARNING_NO_DATA_TO_SAVE = """
Nebyla nalezena žádná data k uložení do souboru '{filename}'
"""
LOG_WARNING_POKUSY = """
Chyba při {operation}: {error_detail} (pokus {current}/{max})
"""
LOG_WARNING_VALUE_HLASY = """
Neplatné číslo hlasů '{hlasy}' pro stranu '{strana}' - přeskočeno
"""

def nastav_logovani(
    verbose: bool = False,
    log_path: str = 'volby_scraper.log',
    max_log_size: int = 1_048_576,  # 1MB
    backup_count: int = 5
) -> None:
    """
    Nastaví logování s rotujícími log soubory a výstupem do konzole.
    Tato funkce nakonfiguruje logování pro záznam 
    informací do konzole a do souboru. 
    V závislosti na hodnotě parametru 'verbose' nastaví
    úroveň logování na buď DEBUG(pro podrobnější logy)
    nebo INFO (pro základní logy).

    Args:
        verbose (bool): Pokud je True, nastaví podrobné logování (DEBUG).
                        Pokud je False, nastaví logování na základní
                        úroveň (INFO). Výchozí hodnota je False.
        log_path (str): Cesta k log souboru (adresář/jméno souboru).
                        Výchozí je 'logs/volby_scraper.log'.
        max_log_size (int): Maximální velikost log souboru před rotací
                            (v bajtech). Výchozí je 1 MB.
        backup_count (int): Počet záložních souborů.
                            Uchová 5 starých log souborů.
    
    Returns:
        None: Funkce nevrací žádnou hodnotu při úspěchu.
    
    Example:
        # Můžeš zadat libovolnou cestu k log souboru, například:
    >>> nastav_logovani(verbose=True, log_path='logs/volby_scraper.log')
        # Testovací zprávy
        logging.info("Toto je info zpráva.")
        logging.debug("Toto je debug zpráva.") 
    """
    # Nastavení úrovně logování
    log_level = logging.DEBUG if verbose else logging.INFO

    # Zkontroluj, jestli je třeba vytvořit adresář
    dir_name = os.path.dirname(log_path)
    if dir_name:  # pokud je dir_name prázdný, nevytvářej nic
        os.makedirs(dir_name, exist_ok=True)

    # Vytvoření rotujícího handleru pro soubor
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_log_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)

    # Vytvoření konzolového handleru
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    console_handler.setFormatter(console_formatter)

    # Získání hlavního loggeru a jeho konfigurace
    logger = logging.getLogger()
    logger.setLevel(log_level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
def validuj_url(url: str, rok_voleb: str = None) -> None:
    # Vrátí None při úspěchu
    """
    Ověřuje validitu zadané URL adresy a případně kontroluje,
    zda obsahuje požadovaný rok voleb.
    Funkce provádí několik kontrol na zadané URL:
    1. zda URL začíná protokolem 'http://' nebo 'https://',
    2. zda URL patří doméně 'volby.cz',
    3. pokud je zadán rok voleb, zkontroluje, 
       zda se teto rok v URL nachází,
    4. ověřuje dostupnost URL provedením HTTP GET požadavku.
    Pokud jakákoliv kontrola selže, vyvolá výjimku 'ValidationError'.

    Args:
        url(str): URL adresa k ověření
        
        rok_voleb(str, optional): řetězec, který má být přítomen 
                                   v URL (např. 'ps2017', 'ps2021')
                                  Pokud není zadán, kontrola 
                                  na tento rok se přeskočí.
    
    Returns:
        None: Funkce nevrací žádnou hodnotu při úspěchu.

    Raises:
        ValidationError: Pokud URL neprojde jednou z kontrol
                         (např. nesprávný protokol, 
                         špatná doména, chybějící rok voleb)
        
        RequestException: Pokud dojde k chybě při HTTP požadavku
                          (např. neexistující doména, 
                          špatné připojení, server nedopovídá)

    Example:
            #úspěšné ověření
        >>> validuj_url("https://www.volby.czu/ps2021", "ps2021")
            #vyvolá ValidationError, protože rok 2022 není v URL
        >>> validuj_url("https://www.volby.czu/ps2021", "ps2022")
    """
    
    if not url.lower().startswith(('http://', 'https://')):
        logging.error(LOG_ERROR_BEGIN)
        raise ValidationError(
            LOG_ERROR_BEGIN
        )
    
    if 'volby.cz' not in url.lower():
        logging.error(LOG_ERROR_DOMENA)
        raise ValidationError(
            LOG_ERROR_DOMENA
        )
    
    if rok_voleb and rok_voleb not in url:
        logging.error(LOG_ERROR_ROK.format(rok=rok_voleb))
        raise ValidationError(
            LOG_ERROR_ROK.format(rok=rok_voleb)
        )
    
    try:
        # Zkusíme udělat GET request pro ověření dostupnosti
        response = requests.get(url, timeout=5)
        # Vrátí chybu (např. 404, 500), jež se zachytí v části except
        response.raise_for_status()
    
    except requests.exceptions.RequestException as e:
        # Zde je potřeba pouze 1 pokus
        zpracuj_vyjimku(e, 0, 1, "ověřování URL")

def parsuj_html(content: str) -> BeautifulSoup:
    """
    Parsuje HTML obsah a vrací objekt BeautifulSoup
    pro snadnou manipulaci a extraci dat.
    Fukce převádí vstupní HTML kód na BeautifulSoup objekt,
    který umožňuje snadnou navigaci a extrakci informací 
    z HTML dokumentu.
    Tento objekt lze použít k vyhledávání elementů,
    získávání textového obsahu nebo atributů HTML tagů.

    Args:
        content(str): HTML obsah stránky ve formě řetězce (string)
    
    Returns:
        BeautifulSoup: Objekt reprezentující parsovaný HTML dokument,
                       umožňující snadnou manipulaci s jeho obsahem
    Example:
        >>> html_content = "<html> +
                            <head> +
                            <title>Testová stránka</title> +
                            </head> +
                            <body><h1>Vítejte!</h1></body> +
                            </html>"
        >>> soup = parsuj_html(html_content)
        >>> print(soup.title.string)
            Testová stránka
        >>> print(soup.h1.text)
            Vítejte!

    Note:
        Funce vyžaduje knihovnu 'BeautifulSoup', která 
        je součástí balíčku 'beautifulsoup4'. 
        Pokud není nainstalována, je třeba ji nainstalovat 
        pomocí 'pip install beautifulsoup'.
    """
       
    return BeautifulSoup(content, 'html.parser')


def stahni_data(url: str, max_pokusu: int = 3) -> requests.Response:
    """
    Stahuje data z URL adresy s možností několika pokusů v případě chyby.
    Funkce se pokusí stáhnout data z uvedené URL adresy.
    V případě, že dojde k chybě při požadavku
    (např. problémy se síťovým připojením, server neodpovídá
    nebo vrací chybu), funkce se pokusí požadavek zopakovat
    až 'max_pokusu' krát.
    Pokud všechny pokusy selžou, funkce vyvolá chybu.

    Args:
        url(str): URL adresa stránky, ze které se mají stáhnout data
        
        max_pokusu(int, optional): Maximální počet pokusů o stažení dat.
                                   Výchozí hodnota jsou 3 pokusy.
    
    Returns:
        requests.Response: Objekt odpovědi (Response), který
                           obsahuje stažená data z URL adresy

    Raises:
        RequestException: Pokud dojde k chybě
                          během všech pokusů o stažení
    
    Example:
        >>> import requests
        >>> url = "https://www.volby.cz/pls/ps2017nss/" +
                  "ps32?xjazyk=CZ&xkraj=14&xnumnuts=8103"
        >>> response = stahni_data(url)
        >>> data = response.text 
            #Získám textový obsah stažené stránky

    Note:
        Funkce používá knihovnu 'requests'.
        Pokud není nainstalována, je třeba ji nainstalovat
        pomocí 'pip install requests'
    """
    
    for pokus in range(max_pokusu):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response
        
        except requests.exceptions.RequestException as e:
            zpracuj_vyjimku(e, pokus, max_pokusu, "stahování dat")
            time.sleep(2) # Počkej před dalším pokusem


def zpracuj_vyjimku(
    e: Exception, pokus: int, max_pokusu: int, operace: str
) -> None:
    """
    Zpracovává výjimky při vykonávání operace a loguje chyby
    podle typu výjimky. Pokud je počet pokusů menší než
    'max_pokusu', vypíše varování a pokračuje v pokusu.
    Při dosažení počtu 'max_pokusu' nebo při vypršení 
    časového limitu vyvolá výjimku.
    
    Args:
        e(Exception): Výjimka, která byla vyvolána během operace
        
        pokus(int): Pořadí aktuálního pokusu (0-indexováno)
        
        max_pokusu(int): Maximální počet pokusů, které se mají
                         provést
        operace(str): Popis operace, která vedla k výjimce
                      (např. název akce, akce API)

    Returns:
        None: Funkce nevrací žádnou hodnotu při úspěchu.
    
    Raises:
        ValidationError: Pokud vypršel datový limit nebo pokud
                         došlo k jiné kritické chybě
    """
    
    if isinstance(e, requests.exceptions.Timeout):
        logging.error(
            LOG_ERROR_TIME_OUT.format(operation=operace, error_detail=e)
        )
        raise ValidationError(
            LOG_ERROR_TIME_OUT.format(operation=operace, error_detail=e)
        ) from e
    
    elif isinstance(e, requests.RequestException):
        logging.error(
            LOG_ERROR_REQUEST.format(operation=operace, error_detail=e)
        )       
        if pokus == max_pokusu - 1: # Poslední pokus
            raise
        logging.warning(
            LOG_WARNING_POKUSY.format(
                operation=operace,
                error_detail=e,
                current=pokus + 1,
                max=max_pokusu
            )
        )


def ziskej_linky_okrsku(
    url: str, max_pokusu: int = 3
) -> List[Okrsek]:
    """
    Získává seznam URL adres jednotlivých okrsků 
    z dané vstupní stránky.
    Funkce stáhne obsah zadané URL a pomocí BeautifulSoup 
    parsuje HTML, aby získala URL adresy jednotlivých okrsků,
    které jsou následně vráceny v seznamu slovníků.
    Každý slovník obsahuje informace o jednom okrsku,
    včetně URL adresy okrsku, čísla obce a názvu obce.

    Args:
        url(str): URL adresa stránky, ze které se získávají ¨
                  URL adresy okrsků
        max_pokusu(int, optional): Maximální počet pokusů o stažení dat.
                                   Výchozí hodnota jsou 3 pokusy.
    
    Returns:
        list[dict]: Seznam slovníků (Okrsek), kde každý obsahuje:
        - 'url'(str): URl adresa okrsku,
        - 'cislo_obce'(str): Číslo obce,
        - 'nazev_obce'(str): Název obce.

    Example:
        >>> url = "https://www.volby.cz/pls/ps2017nss/" +
                  "ps32?xjazyk=CZ&xkraj=14&xnumnuts=8103"
        >>> okrsky = ziskej_linky_okrsku(url)
        >>> okrsky[0]

    Note:
        Funkce předpokládá, že všechny odkazy v HTML 
        odpovědi jsou ve formátu 'ps311' a obsahují 
        parametry s číslem obce.
        Pokud se struktura stránky změní, může být nutné 
        upravit selektory.
    """
    
    unique_urls = set()
    obce: List[Okrsek] = []

    response = stahni_data(url, max_pokusu)
    soup = parsuj_html(response.text)   

    for row in soup.select('table tr'):
        link = row.select_one('td:nth-child(1) a[href*="ps311"]')
        if link:
            href = link.get('href')
            full_url = BASE_URL + href
            if full_url not in unique_urls:
                unique_urls.add(full_url)
                cislo_obce = href.split('xobec=')[1].split('&')[0]
                nazev_obce_cell = row.select_one('td.overflow_name')
                nazev_obce = (
                    nazev_obce_cell.text.strip()
                    if nazev_obce_cell
                    else None
                )
                obce.append(
                    Okrsek(
                        url=full_url,
                        cislo_obce=cislo_obce,
                        nazev_obce=nazev_obce
                    )
                )
            
    return obce
        

def ziskej_data_obce(url: str, max_pokusu: int = 3) -> ObecData:
    """
    Získává detailní volební data pro konkrétní obce z dané URL.
    Funkce stáhne obsah zadané URL a pomocí BeautifulSoup 
    parsuje HTML, aby získala detailní volební výsledky 
    pro konkrétní obec.
    Výsledky jsou vráceny ve formě slovníku (ObecData), který
    obsahuje informace o obci, počtech voličů, vydaných obálkách,
    platných hlasech a výsledcích jednotlivých politických stran.

    Args:
        url(str): URL adresa stránky obsahující
                  volební data pro konkrétní obec.
        max_pokusu(int, optional): Maximální počet pokusů 
                                   o stáhnutí stránky.
                                   Výchozí hodnota je 3.

    Returns:
        ObecData: Slovník s volebními data pro danou obec, 
                  který obsahuje:
        - 'obec'(str): Název obce,
        - 'volici'(str): Počet registrovaných voličů,
        - 'vydane_obalky'(int): Počet vydaných volebních obálek,
        - 'platne_hlasy'(int): Počet platných hlasů,
        - 'strany'(List[Strana]): Seznam politických stran
                                  a počtu hlasů pro každou stranu.

    Raises:
        DataParsingError: Pokud dojde k chybě při parsování dat.
        
        ValueError: Pokud není možné text převést na číslo
            (například pokud obsahuje jiné než číselné znaky)
    
    
    Examples:
         >>> url = "https://www.volby.cz/pls/ps2017nss/"
         >>> data = ziskej_data_obce(url)
         >>> print(data)
             {'obec': 'Albrechtice',
              'volici': 3173,
              'vydane_obalky': 1957,
              'platne_hlasy': 1944,             
              'strany': [{'strana': 'Občanská demokratická strana',
                          'hlasy': 109},
                         {'strana': 'Řád národa - Vlastenecká unie',
                          'hlasy': 4},
                         {'strana': 'CESTA ODPOVĚDNÉ SPOLEČNOSTI',
                          'hlasy': 2},
                          ...
               ]
             }
    
    Note:
        Funkce předpokládá, že stránka obsahuje 
        specifické HTML elementy pro jednotlivé údaje.
        Při zpracování počtu hlasů pro strany je 
        počítáno s tím, že hlasy jsou uvedeny v textové 
        podobě bez čárky. 
        Pokud jsou data obce podezřelá, zachytí je výjimka 
        a zaloguje jako chybu pro danou obec.
    """
    
    response = stahni_data(url, max_pokusu)
    soup = parsuj_html(response.text)
    
    # Najdi název obce
    obec_text = najdi_text_nebo_chybu(
        soup, 'h3:-soup-contains("Obec:")', "název obce"
    )
    jmeno_obce = obec_text.replace("Obec:", "").strip()
    
    # Najdi počet voličů
    volici_text = najdi_text_nebo_chybu(
        soup, 'td[headers="sa2"]', "počet voličů"
    )
    volici = ocisti_cislo(volici_text)
    
    # Najdi počet vydaných obálek
    vydane_text = najdi_text_nebo_chybu(
        soup, 'td[headers="sa3"]', "počet vydaných obálek"
    )
    vydane_obalky = ocisti_cislo(vydane_text)
    
    # Najdi počet platných hlasů
    platne_text = najdi_text_nebo_chybu(
        soup, 'td[headers="sa6"]', "počet platných hlasů"
    )
    platne_hlasy = ocisti_cislo(platne_text)
    
    # Najdi strany a počet hlasů
    strany_data: List[Strana] = []
    for table in soup.select('table')[1:]:
        for row in table.select('tr:nth-child(n+3)'):
            cells = row.select('td')
            if len(cells) >= 3:
                strana = cells[1].text.strip()
                hlasy_text = cells[2].text.strip()
                logging.debug(
                    LOG_DEBUG_LOADED_DATA.format(
                        strana=strana, 
                        hlasy=hlasy_text
                    )
                )
                # Zkontrolujeme, zda máme platný řádek
                if not je_validni_radek(strana, hlasy_text):
                    logging.debug(
                        LOG_DEBUG_SKIP_ROW.format(
                            strana=strana, hlasy=hlasy_text
                        )
                    )
                    continue  # Přeskoč tento řádek

                try:
                    hlasy = ocisti_cislo(hlasy_text)                    
                    strany_data.append(Strana(strana=strana, hlasy=hlasy))
                
                except ValueError:
                    logging.warning(
                        LOG_WARNING_VALUE_HLASY.format(
                            hlasy=hlasy_text, strana=strana
                        )
                    )
                    continue # Přeskoč tento řádek
                
                except DataParsingError as e:
                    logging.error(
                        LOG_ERROR_PARSING_DATA.format(error_detail=e)
                    )
                    raise               
                                  
    return (
        ObecData(obec=jmeno_obce,
        volici=volici,
        vydane_obalky=vydane_obalky,
        platne_hlasy=platne_hlasy,
        strany=strany_data)
    )



def najdi_text_nebo_chybu(
    soup: BeautifulSoup, selector: str, popis: str
) -> str:
    """
    Najde textový obsah HTML elementu podle CSS selektoru, 
    nebo vyvolá výjimku, pokud daný element neexistuje.
    Tato pomocná funkce slouží ke spolehlivému získání 
    textových dat z HTML pomocí knihovny BeautifulSoup. 
    Pokud není požadovaný element nalezen, zaloguje 
    chybovou zprávu a vyvolá výjimku typu DataParsingError.

    Args:
        soup (BeautifulSoup): Objekt BeautifulSoup, který 
                              reprezentuje HTML dokument.
        selector (str): CSS selektor pro vyhledání 
                        požadovaného elementu.
        popis (str): Popis hledaného prvku 
                     (používá se pro logování chyb).

    Returns:
        str: Textový obsah nalezeného elementu se zbavením 
             počátečních a koncových mezer.

    Raises:
        DataParsingError: Pokud není element v HTML nalezen.

    Example:
        >>> from bs4 import BeautifulSoup
        >>> html = "<html><body> + 
                    <h3>Obec: Albrechtice</h3> +
                    </body></html>"
        >>> soup = BeautifulSoup(html, 'html.parser')
        >>> najdi_text_nebo_chybu(soup, 'h3', 'název obce')
        'Obec: Albrechtice'

    Note:
        Tato funkce se používá zejména při extrakci 
        údajů jako je název obce, počet voličů atd., 
        a zajišťuje, že v případě neúspěchu bude chyba
        zachycena a popsána.
    """
    
    element = soup.select_one(selector)
    
    if element is None:
        logging.error(f"Nepodařilo se najít element: {popis}")
        raise DataParsingError(f"Chybí element: {popis}")
    
    return element.text.strip()


def ocisti_cislo(text: str) -> int:
    """
    Očistí číslo od nežádoucích znaků (např. mezery, 
    nerozdělitelná mezera) a převede ho na celé číslo.
    Tato pomocná funkce přijímá textový řetězec, který 
    může obsahovat mezery nebo speciální znaky
    (např. nerozdělitelná mezera, která je často používána
    v HTML pro oddělování tisíců) a odstraní tyto znaky.
    Poté převede upravený text na celé číslo (integer).

    Args:
        text(str): Vstupní textový řetězec, který obsahuje 
                   číslo ve formátu s nežádoucími znaky.

    Returns:
        int: Čisté číslo (integer), které je výsledkem
             očištění textového řetězce.

    Raises:
        ValueError: Pokud není možné text převést na číslo       
                    (například pokud obsahuje jiné než číselné znaky).

    Examples:
        >>> ocisti_cislo('1 234')
            1234
        >>> ocisti_cislo('1\xa0234')
            1234
        >>> ocisti_cislo('5000')
            5000
    """
    return int(text.replace('\xa0', '').replace(' ', ''))


def je_validni_radek(strana:str, hlasy_text: str) -> bool:
    """
    Tato pomocná funkce slouží k ověření, zda daný řádek 
    (například z nějakých dat nebo tabulky) je platný 
    na základě určitých kritérií. 
    Funkce vrací True, pokud jsou splněny podmínky:
    - strana není rovna "-" 
      ("-" je označení chybějících nebo neplatných dat)
    - hlasy_text není rovno "-", 
    - hlasy_text není prázdný řetězec "".
    Jinak řečeno, funkce vrátí False, pokud je alespoň jedna 
    z těchto hodnot, buď "-" nebo prázdný řetězec u hlasy_text.
    Funkce kontroluje, zda data nejsou označena jako neplatná 
    nebo chybějící, a pokud jsou všechna data platná, vrátí True.
    
    Args:
        strana (str): Název strany 
        hlasy_text (str): Textové vyjádření počtu hlasů 

    Returns:
        bool:
            - True: pokud vstupní argumenty nejsou rovny "-" nebo ""
            - False: pokud alespoň jedna hodnota ze vstupních 
              argumentů je rovna "-" nebo ""
    
    Example:
        >>> je_validni_radek("Občanská demokratická strana", "153")
        True
        >>> je_validni_radek("-", "45")
        False
        >>> je_validni_radek("Strana zelených", "-")
        False
        >>> je_validni_radek("Pirátská strana", "")
        False
    """
    return not (strana == "-" or hlasy_text == "-" or hlasy_text == "")
  

def zkontroluj_vstupy() -> tuple[str, str]:
    """
    Zkontroluje správnost vstupních argumentů programu
    (URL adresu okresu a název výstupního souboru).
    Funkce ověřuje, že uživatel poskytl správný 
    počet argumentů (2), a že tyto argumenty obsahují 
    URL adresu okresu a název výstupního souboru. 
    Pokud není zadaný správný počet argumentů,
    funkce vypíše chybovou zprávu a ukončí program.
    
    Args:
        Argumenty jsou získávány z 'sys.argv'
        (vstupní argumenty příkazového řádku)
    
    Returns:
        tuple[str, str]: Dvojice obsahující:
            - str: URL adresa okresu 
                   (první argument)
            - str: název výstupního souboru 
                   (druhý argument)

    Raises:
        SystemExit: Pokud není zadán správný počet 
                    argumentů nebo jsou nesprávně formátovány,
                    program vypíše chybovou zprávu a 
                    ukončí se s kódem 1.

    Examples:
        import sys
        sys.argv = (
            ['election_scraper.py',
            'https://www.volby.cz/pls/ps2017nss/ +
            ps32?xjazyk=CZ&xkraj=14&xnumnuts=8102',
            'vysledky.csv']
        )
        >>> zkontroluj_vstupy()
            ('https://www.volby.cz/pls/ps2017nss/ +
            ps32?xjazyk=CZ&xkraj=14&xnumnuts=8102',
            'vysledky.csv'
            )

            sys.argv = (
                ['election_scraper.py',
                'https://www.volby.cz/pls/ps2017nss/ +
                ps32?xjazyk=CZ&xkraj=14&xnumnuts=8102'
                ]
            )
        >>> zkontrolu_vstupy()
            Chyba: Musíte zadat dva argumenty -
               URL okresu a název výstupního souboru.
            Chyba: Nsprávný počet argumentů!
            Použití: python election_scraper.py
                 <URL_okresu> <vystupni_soubor.csv>
            Příklad: python election_scraper.py
                 "https://volby.cz/..." "vysledky.csv"
            SystemExit: 1
    """    
    
    if len(sys.argv) != 3:
        logging.error(LOG_ERROR_ARGUMENTS_COUNT)
        print("\n" + SEPARATOR)
        print(
            Fore.LIGHTYELLOW_EX + 
            MSG_ERROR_ARGUMENTS_COUNT.format(script_name=sys.argv[0])
        )
        print(SEPARATOR + "\n")
        sys.exit(1)

    url_okresu = sys.argv[1]
    vystupni_soubor = sys.argv[2]
    return url_okresu, vystupni_soubor


def ziskej_obce(url_okresu) -> list[dict]:
    """
    Validuje URL adresu a získává seznam obcí ke zpracování.
    Funkce nejprve validuje zadanou URL adresu okresu, 
    a pokud je platná, pokračuje získáním seznamu obcí, 
    které budou dále zpracovávány.
    Pokud není nalezen žádný odkaz na obce,
    funkce vypíše chybovou hlášku a ukončí program.

    Args:
        url_okresu(str): URL adresa okresu, ze které
                         budou získány odkazy obce
    Returns:
        list[dict]: Seznam slovníků, kde každý slovník 
                    obsahuje informace o obci.
            Každý slovník má následující klíče:
                - 'url'(str): URL adresa okrsku pro danou obec
                - 'cislo_obce'(str): Číslo obce
                - 'nazev_obce'(str): Název obce
    Raises:
        ValidationError: Pokud je URL neplatná 
                         (zpracováno přímo zde s sys.exit).
        NoDataFoundError: Vyvolá (předá dál) výjimnku, pokud
                          funkce ziskej_linky_okrsku 
                          nenajde žádné obce.
        requests.exceptions.RequestException: 
                          Zachytává chybu při stahování dat
        Exception: Pokud dojde k jakékoliv neočekávané chybě.
        
    Examples:
        >>> url_okresu = "https://www.volby.cz/pls/ps2017nss/" +
                         "ps32?xjazyk=CZ&xkraj=14&xnumnuts=8103"
        >>> obce = ziskej_obce(url_okresu)
        >>> print(obce)    
            [{'url': 'https://www.volby.cz/pls/ps2017nss/
            ps311?xjazyk=CZ&xkraj=14&xobec=598925&xvyber=8103'},
              'cislo_obce': '598925',
              'nazev_obce': 'Albrechtice'}]

    Note:
        Tato funkce neukončuje program při nenalezení obcí.
        Zachytává NoDataFoundError a znovu ji vyvolává.
        ValidationError funkci ukončuje.
    """
    
    print(
        "\n" + Fore.LIGHTCYAN_EX + 
        MSG_INFO_VALIDATION.format(url=url_okresu) + "\n"
    )
    
    try:
        validuj_url(url_okresu)
        logging.info(LOG_INFO_URL_VALIDATED.format(url=url_okresu))
    except ValidationError as e:
        logging.error(
            LOG_ERROR_URL_VALIDATION.format(
                url=url_okresu, error_detail=e
            )
        )
        print("\n" + SEPARATOR)
        print(
            Fore.LIGHTYELLOW_EX + 
            MSG_ERROR_URL_VALIDATION.format(
                url=url_okresu, error_detail=e
            )
        )
        print(SEPARATOR + "\n")
        sys.exit(1)
    
    # Získání seznamu obcí
    print("\n" + Fore.LIGHTCYAN_EX + MSG_INFO_GETTING_LIST + "\n")
    
    logging.info(LOG_INFO_GETTING_OBCE.format(url=url_okresu))
    try:
        obce = ziskej_linky_okrsku(url_okresu)
        if not obce: # Kontrola, zda se obce opravdu našly
            raise NoDataFoundError(
                LOG_RAISE_NO_DATA_FOUND.format(url=url_okresu)
            )
        logging.info(LOG_INFO_COUNT_OBCE.format(count=len(obce)))
        return obce
 
    except NoDataFoundError as e:
        # Zde chybu zalogujeme, a pak znovu vyvoláme, 
        # A zpracujeme v hlavní funkci
        logging.error(LOG_ERROR_GETTING_LIST.format(error_detail=e))       
        print("\n" + SEPARATOR)
        print(
            Fore.LIGHTYELLOW_EX + 
            MSG_WARNING_NO_DATA_FOUND.format(url=url_okresu)
        )
        print(SEPARATOR + "\n")
        raise #Znovu vyvoláme zachycenou výjimku NoDataFoundError
    
    except requests.exceptions.RequestException as e:
        # Zachytíme chybu při stahování v ziskej_linky_okrsku
        logging.error(
            LOG_ERROR_REQUEST_FAILED.format(
            url=url_okresu, error_detail=e
            ), exc_info=True
        ) 
        # exc_info=True pro detailní Traceback
        print("\n" + SEPARATOR)
        print(
            Fore.LIGHTYELLOW_EX + 
            MSG_ERROR_REQUEST_FAILED.format(
                url=url_okresu, error_detail=e
            )
        )
        print(SEPARATOR + "\n")
        sys.exit(1)
    
    except Exception as e:
        # Tady zachytíme jakékoli jiné nečekané chyby
        logging.error(
            LOG_ERROR_UNEXPECTED.format(
                operation=f"získávání seznamu obcí", error_detail=e
            ), exc_info=True
        )
        print("\n" + SEPARATOR)
        print(
            Fore.LIGHTYELLOW_EX + 
            MSG_ERROR_UNEXPECTED.format(
                operation=f"získávání seznamu obcí", error_detail=e
            )
        )
        print(SEPARATOR + "\n")
        sys.exit(1)
   

def zpracuj_obce(obce) -> tuple[list, dict]:
    """
    Zpracuje seznam obcí a získá volební data pro každou obec.
    Funkce projde seznam obcí, pro každou obec stáhne a
    zpracuje její volební data, včetně počtu voličů, 
    vydaných obálek, platných hlasů a hlasů pro 
    jednotlivé strany.
    Vytvoří výstupní seznam, který obsahuje výsledky 
    pro každou obec, a také statistiky o celkovém počtu 
    zpracovaných obcí, celkovém počtu voličů a platných hlasů.

    Args:
        obce (list): Seznam slovníků, kde každý slovník 
                     obsahuje informace o obci, 
                     včetně URL adresy a čísla obce.

    Returns:
        tuple: Dvojice, kde:
            - list: Seznam výsledků volebních dat pro každou obec;
                    každý výsledek obsahuje informace jako 
                    číslo obce, název obce, voliče, vydané obálky, 
                    platné hlasy a hlasy pro jednotlivé strany.
            
            - dict: Statistiky zpracování, obsahující:
                - 'zpracovane_obce': Počet zpracovaných obcí
                - 'chyby': Počet chyb při zpracování obcí
                - 'celkem_volicu': Celkový počet voličů pro všechny
                                   zpracované obce
                - 'celkem_platnych_hlasu': Celkový počet platných hlasů
                                           pro všechny zpracované obce

    Examples:
        obce = (
            [{'url': 'https://www.volby.cz/pls/ps2021nss/
            ps311?xjazyk=CZ&xkraj=14&xobec=598925',
            'cislo_obce': '598925', 
            'nazev_obce': 'Albrechtice'}, ...
            ]
        )
        >>> vysledky, stats = zpracuj_obce(obce)
        vysledky
        [{'Číslo obce': '598925', 'Název obce': 'Albrechtice',
          'Voliči': 3173,'Vydané obálky': 1957, 
          'Platné hlasy': 1944, 'ANO 2011': 635, ...}, ...
        ]
        stats
        {'zpracovane_obce': 17, 'chyby': 0, 
         'celkem_volicu': 106196,
         'celkem_platnych_hlasu': 106196}
    
    Note:
        Funkce používá knihovnu 'tqdm'.
        Pokud není nainstalována, je třeba ji nainstalovat
        pomocí 'pip install tqdm'
    """
    
    vysledky = []
    # Přidáme statistiky
    stats = {
        'zpracovane_obce': 0,
        'chyby': 0,
        'celkem_volicu': 0,
        'celkem_platnych_hlasu': 0
    }

    print("\n" + Fore.LIGHTCYAN_EX + MSG_INFO_PROCESSING_DATA + "\n")
    logging.info(LOG_INFO_PROCESSING_OBCE)
    
    total_obce = len(obce)
    print(
        "\n" + Fore.LIGHTCYAN_EX + 
        MSG_INFO_COUNT_OBCE.format(total=total_obce) + "\n"
    )
    
    # Zpracování každé obce s progress barem
    for i, obec in enumerate(
        tqdm(obce, desc="Zpracovávám obce", unit="obec")
    ):
        obec_nazev = obec['nazev_obce']
        obec_cislo = obec['cislo_obce']
        # Výpis aktuální obce
        print(
            MSG_INFO_PROCESSING_OBCE.format(
            cislo=i+1, total=total_obce, 
            obec_nazev=obec_nazev, obec_cislo=obec_cislo
            )
        )
        
        try:
            logging.debug(
                LOG_DEBUG_PROCESSING_OBCE.format(
                    obec_nazev=obec_nazev,
                    obec_cislo=obec_cislo,
                    url=obec['url']
                )
            )
            data = ziskej_data_obce(obec['url'])
               
            radek = {
                'Číslo obce': obec_cislo,
                'Název obce': data['obec'],
                'Voliči': data['volici'],
                'Vydané obálky': data['vydane_obalky'],
                'Platné hlasy': data['platne_hlasy']
            }
               
            for strana in data['strany']:
                radek[strana['strana']] = strana['hlasy']
                   
            vysledky.append(radek)

            # Aktualizace statistik
            stats['zpracovane_obce'] += 1
            stats['celkem_volicu'] += data['volici']
            stats['celkem_platnych_hlasu'] += data['platne_hlasy']
            logging.debug(
                LOG_DEBUG_OBCE_PROCESSED.format(
                    obec_nazev=obec_nazev,
                    obec_cislo=obec_cislo
                )   
            )

        except (ValueError, DataParsingError) as e:
            vypis_chybu(
                LOG_ERROR_PARSING_ERROR, obec_nazev, obec_cislo, e
            )
            stats['chyby'] += 1
            continue # Pokračuj na další obec
           
        except requests.exceptions.RequestException as e:
            vypis_chybu(
                LOG_ERROR_REQUEST_OBCE_FAILED, obec_nazev, obec_cislo, e
            )
            stats['chyby'] += 1
            continue # Pokračuj na další obec
        
        except Exception as e:
            logging.error(
                LOG_ERROR_UNEXPECTED_OBCE.format(
                    obec_nazev=obec_nazev,
                    obec_cislo=obec_cislo,
                    error_detail=e
                ), exc_info=True
            )
            print("\n" + SEPARATOR)
            print(
                Fore.LIGHTYELLOW_EX + MSG_ERROR_UNEXPECTED.format(
                    operation=(
                        f"zpracování obce {obec_nazev} ({obec_cislo}). "
                        "Tato obec bude přeskočena."
                    ),
                    error_detail=e
                )
            )
            print(SEPARATOR + "\n")
            stats['chyby'] += 1
            continue # Pokračuj na další obec
    
    print("\n")
    logging.info(LOG_INFO_OBCE_PROCESSED)
    return vysledky, stats


def vypis_chybu(
    a: str, 
    obec_nazev: str, 
    obec_cislo: str, chyba: str
) -> None:
    """
    Vypíše do logu a na konzoli chybové hlášení týkající se dané obce.

    Args:
        a (str): Šablona formátovacího řetězce 
                 pro logování chybové události.
        obec_nazev (str): Název obce.
        obec_cislo (str): Číslo obce.
        chyba (str): Podrobnosti o chybě.

    Returns:
        None: Funkce nevrací žádnou hodnotu při úspěchu.

    Example:
        >>> vypis_chybu(
                LOG_ERROR_PARSING_ERROR, "Praha", "001", 
                "Chyba při parsování dat"
            )
    """
    logging.error(
        a.format(
            obec_nazev=obec_nazev, 
            obec_cislo=obec_cislo, 
            error_detail=chyba
        ), exc_info=True
    )
    
    print("\n" + SEPARATOR)
    print(
        Fore.LIGHTYELLOW_EX + 
        MSG_WARNING_PROCESSING_ERROR.format(
            obec_nazev=obec_nazev, 
            obec_cislo=obec_cislo, 
            error_detail=chyba
        )
    )
    print(SEPARATOR + "\n")


def uloz_soubor(
    vysledky, vystupni_soubor, format_typ, ulozit_funkce
) -> None:
    """
    Uloží výsledky do souboru pomocí předané funkce.
    Tato funkce zkontroluje, zda jsou k dispozici výsledky 
    k uložení, vypíše informaci o cílovém souboru a formátu, 
    a poté zavolá předanou funkci `ulozit_funkce` k zápisu dat.
    V případě chyby při zápisu je zaznamenána chyba do logu.

    Args:
        vysledky (any): Data, která mají být uložena.
                        Může to být seznam, slovník nebo jiný datový typ.
        vystupni_soubor (str): Název souboru, včetně přípony,
                               do kterého se mají výsledky uložit.
        format_typ (str): Typ formátu (např. 'csv', 'json'),
                          který určuje formát ukládání.
        ulozit_funkce (callable): Funkce, která provádí samotný 
                          zápis dat do souboru. Měla by přijmout 
                          dva argumenty: data a název souboru.

    Returns:
        None: Funkce nevrací žádnou hodnotu při úspěchu.

    Raises:
        OSError: Pokud dojde k chybě při ukládání, je vyhozena
                 výjimka, která je následně zachycena a 
                 zpracována v hlavní funkci

        FileSavingError: Pokud dojde k chybnému uložení je
                         vyvolána výjimka
    Note:
        Ujistěte se, že `ulozit_funkce` správně pracuje 
        s předanými daty a souborem.
    """
    
    if not vysledky:
        logging.warning(
            LOG_WARNING_NO_DATA_TO_SAVE.format(filename=vystupni_soubor)
        )
        print("\n" + SEPARATOR)
        print(Fore.LIGHTYELLOW_EX + MSG_WARNING_NO_DATA_SAVE)
        print(SEPARATOR + "\n")
        raise FileSavingError(LOG_ERROR_SAVING_FAILED)
    
    print(
        Fore.LIGHTCYAN_EX + MSG_INFO_SAVING.format(
            filename=vystupni_soubor, format=format_typ.upper()
        )   
    )
    try:
        ulozit_funkce(vysledky, vystupni_soubor)
        print(
            Fore.LIGHTGREEN_EX + 
            MSG_INFO_SUCCESS_SAVE.format(filename=vystupni_soubor)
        )
        logging.info(
            LOG_INFO_SAVE_SUCCESS.format(filename=vystupni_soubor)
        )
    
    except OSError as e:
        logging.error(
            LOG_ERROR_SAVE_FAILED.format(
                filename=vystupni_soubor, error_detail=e
            ), exc_info=True
        )
        print("\n" + SEPARATOR)
        print(
            Fore.LIGHTYELLOW_EX + 
            MSG_ERROR_SAVE_FAILED.format(
                filename=vystupni_soubor, error_detail=e
            )
        )
        print(SEPARATOR + "\n")
        raise FileSavingError(LOG_ERROR_SAVING_FAILED)
    
    except Exception as e:
        logging.error(
            LOG_ERROR_UNEXPECTED.format(
                operation=f"ukládání souboru'{vystupni_soubor}'",
                error_detail=e
            ), exc_info=True
        )
        print("\n" + SEPARATOR)
        print(
            Fore.LIGHTYELLOW_EX + MSG_ERROR_UNEXPECTED.format(
                operation=f"ukládání souboru '{vystupni_soubor}'",
                error_detail=e
            )    
        )
        print(SEPARATOR + "\n")
        raise FileSavingError(LOG_ERROR_SAVING_FAILED)
           


def uloz_vysledky(vysledky, vystupni_soubor) -> None:
    """
    Ukládá výsledky do souboru podle zadané přípony (CSV, JSON, XML).
    Funkce rozpozná příponu souboru z názvu zadaného uživatelem a
    podle ní vybere správnou metodu pro uložení dat.
    Podporované formáty jsou CSV, JSON a XML. V případě 
    nepodporovaného formátu funkce ukončí program s chybovou hláškou.

    Args:
        vysledky (list): Seznam slovníků obsahující volební data,
                         která byla získána a zpracována
                         funkcí `zpracuj_obce`.
        vystupni_soubor (str): Název souboru, včetně přípony,
                               do kterého se mají výsledky uložit.

    Returns:
        None: Funkce nevrací žádnou hodnotu při úspěchu.

    Raises:
        SystemExit: Pokud je zadaný formát souboru nepodporován.

        UnsupportedFormatError: Pokud dojde k zadání nepodorovného
                    formátu souboru, je vyvolána výjimka, která
                    je následně zachycena a zpracována v hlavní
                    funkci

    Examples:
        vystupni_soubor = "karvina.json"
        uloz_vysledky(vysledky, vystupni_soubor)
        (Tato funkce uloží výsledky do souboru karvina.json.)
        
    Notes:
        Funkce podporuje následující formáty souborů:
        - CSV (.csv)
        - JSON (.json)
        - XML (.xml)
    """
    # Automatické rozpoznání přípony
    pripona = vystupni_soubor.split('.')[-1].lower()

    if pripona == 'csv':
        uloz_soubor(vysledky, vystupni_soubor, 'csv', uloz_do_csv)
    elif pripona == 'json':
        uloz_soubor(vysledky, vystupni_soubor, 'json', uloz_do_json)
    elif pripona == 'xml':
        uloz_soubor(vysledky, vystupni_soubor, 'xml', uloz_do_xml)
    else:
        print("\n" + SEPARATOR)
        print(
            Fore.LIGHTYELLOW_EX + 
            MSG_ERROR_UNSUPPORTED_FORMAT.format(format_typ=pripona)
        )
        print(SEPARATOR + "\n")
        raise UnsupportedFormatError(
            LOG_ERROR_UNSUPPORTED_FORMAT.format(format_typ=pripona)
        )
 

def uloz_do_csv(vysledky, vystupni_soubor) -> None:
    """
    Uloží volební výsledky do CSV souboru.
    Funkce zpracuje seznam volebních výsledků a uloží je do CSV souboru.
    Sloupce souboru budou obsahovat základní informace o obcích a
    volebních výsledcích, včetně všech stran a jejich hlasů,
    které se vyskytují v datech.
    Pokud některé výsledky nemají hodnotu pro některý sloupec,
    v CSV souboru bude tento sloupec prázdný.
    Pokud nejsou k dispozici žádná data, funkce vypíše chybovou zprávu.

    Args:
        vysledky (list): Seznam slovníků obsahujících volební
                         výsledky k uložení.
                         Každý slovník reprezentuje jednu obec
                         s jejími volebními výsledky.
        vystupni_soubor (str): Cesta k výstupnímu souboru CSV,
                               kam budou výsledky uloženy.

    Returns:
        None: Funkce nevrací žádnou hodnotu při úspěchu.

    Raises:
        OSError: Pokud dojde k chybě při ukládání souboru.
                 Tato výjimka je však pravděpodobně již
                 zachycena a zpracována funkcí 'uloz_soubor'

    Examples:
        vysledky = [
             {
                 "Číslo obce": "598925",
                "Název obce": "Albrechtice",
                "Voliči": 3173,
                 "Vydané obálky": 1957,
                 "Platné hlasy": 1944,
                 "Občanská demokratická strana": 109,
                 "Řád národa - Vlastenecká unie": 4
             }
         ]
        >>> uloz_do_csv(vysledky, "vysledky.csv")
            (Uloží výsledky voleb do souboru vysledky.csv)

    
    Notes:
        Funkce automaticky přidá nové sloupce pro všechny strany,
        které se objeví v datech.
        Pokud nějaký výsledek neobsahuje určité sloupce
        (např. číslo obce, názvy stran),
        bude tento sloupec v CSV souboru prázdný.
    """
    
    sloupce = [
        'Číslo obce',
        'Název obce',
        'Voliči',
        'Vydané obálky',
        'Platné hlasy'
    ]
    for vysledek in vysledky:
        for klic in vysledek.keys():
            if klic not in sloupce:
                sloupce.append(klic)
            
    with open(
        vystupni_soubor, 'w', newline='', encoding='utf-8-sig'
    ) as f:
        writer = csv.DictWriter(f, fieldnames=sloupce)
        writer.writeheader()
        writer.writerows(vysledky)
        

def uloz_do_json(vysledky, vystupni_soubor) -> None:
    """
    Uloží volební výsledky do JSON souboru.
    Funkce zpracuje seznam volebních výsledků a uloží je do JSON souboru.
    Každý volební výsledek je uložen jako slovník, kde
    klíče představují různé údaje o obcích a volebních stranách,
    a hodnoty představují odpovídající data.
    Výsledky jsou uložené v dobře formátovaném JSON formátu
    pro snadnou čitelnost.

    Args:
        vysledky (list): Seznam slovníků obsahujících volební výsledky
                         pro jednotlivé obce.
        vystupni_soubor (str): Cesta k výstupnímu souboru JSON,
                               kam budou výsledky uloženy.

    Returns:
        None: Funkce nevrací žádnou hodnotu při úspěchu.

    Raises:
        OSError: Pokud dojde k chybě při ukládání souboru.
                 Tato výjimka je však pravděpodobně již
                 zachycena a zpracována funkcí 'uloz_soubor'

    Examples:
        vysledky = [
             {
                 "Číslo obce": "598925",
                "Název obce": "Albrechtice",
                "Voliči": 3173,
                 "Vydané obálky": 1957,
                 "Platné hlasy": 1944,
                 "Občanská demokratická strana": 109,
                 "Řád národa - Vlastenecká unie": 4
             }
         ]
        >>> uloz_do_json(vysledky, "vysledky.json")
            (Uloží výsledky voleb do souboru vysledky.json)

    
    Notes:
        Funkce používá formátování s odsazením (indent=2),
        aby výstupní JSON byl přehledný a snadno čitelný.
        Funkce neprovádí žádné specifické validace vstupních dat,
        předpokládá, že `vysledky` obsahují seznam slovníků
        s volebními daty.
    """
    
    with open(vystupni_soubor, 'w', encoding='utf-8') as f:
        json.dump(vysledky, f, ensure_ascii=False, indent=2)
       

def uloz_do_xml(vysledky, vystupni_soubor) -> None:
    """
    Uloží volební výsledky do XML souboru.
    Funkce zpracuje seznam volebních výsledků a uloží je 
    do XML souboru, přičemž každý volební výsledek je zapsán 
    jako XML element.
    Každá obec bude reprezentována jako samostatný XML element
    s podřízenými elementy, které odpovídají různým údajům o obci a
    volebních stranách. Výsledky jsou uloženy v dobře formátovaném
    XML formátu s deklarací kódování UTF-8.

    Args:
        vysledky (list): Seznam slovníků obsahujících volební výsledky
                         pro jednotlivé obce.
        vystupni_soubor (str): Cesta k výstupnímu XML souboru, kam budou
                               výsledky uloženy.

    Returns:
        None: Funkce nevrací žádnou hodnotu při úspěchu.

    Raises:
        OSError: Pokud dojde k chybě při ukládání souboru.
                 Tato výjimka je však pravděpodobně již
                 zachycena a zpracována funkcí 'uloz_soubor'

    Examples:
         vysledky = [
             {
                 "Číslo obce": "598925",
                 "Název obce": "Albrechtice",
                 "Voliči": 3173,
                 "Vydané obálky": 1957,
                 "Platné hlasy": 1944,
                 "Občanská demokratická strana": 109,
                 "Řád národa - Vlastenecká unie": 4
             }
         ]
        >>> uloz_do_xml(vysledky, "vysledky.xml")
            (Uloží výsledky voleb do souboru vysledky.xml)

    Notes:
        Funkce vytváří XML soubor s deklarací UTF-8 a přidává do něj
        data ve formátu, kde každá obec je reprezentována jako
        XML element `<obec>`. Každý volební údaj o obci je zapsán jako
        podřízený element, např. `<Číslo obce>`. 
        Funkce používá formátování s odsazením ET.indent, aby 
        výstupní XML byl přehledný; tato funkce je dostupná 
        od Pythonu 3.9+. Pokud se používá starší verze, bude potřeba 
        odsazení implementovat ručně nebo použít jiný přístup.
    """
    
    root = ET.Element('vysledky')
    for vysledek in vysledky:
        obec = ET.SubElement(root, 'obec')
        for klic, hodnota in vysledek.items():
            ET.SubElement(obec, klic).text = str(hodnota)
    strom = ET.ElementTree(root)
    
    # Přidáme odsazení 
    ET.indent(strom, space="  ")
    
    # Ulož strom do souboru
    strom.write(vystupni_soubor, encoding='utf-8', xml_declaration=True)
             

def vypis_statistiky(stats: dict, cas_zacatku: float) -> None:
    """
    Vytvoří a vypíše statistiku zpracování volebních dat včetně
    doby zpracování a volební účasti.
    Funkce zpracuje předané statistiky o volebních výsledcích a
    vypíše souhrnné informace o době zpracování, počtu zpracovaných obcí,
    počtu chyb, celkovém počtu voličů a platných hlasů.
    Dále vypočítá průměrnou volební účast na základě celkového počtu
    voličů a platných hlasů.
 
    Args:
        stats (dict): Slovník obsahující statistiky zpracování volebních dat.
            Očekávané klíče:
            - 'zpracovane_obce': int - počet zpracovaných obcí
            - 'chyby': int - počet chyb při zpracování
            - 'celkem_volicu': int - celkový počet voličů
            - 'celkem_platnych_hlasu': int - celkový počet platných hlasů
        cas_zacatku (float): Časová značka (epoch time) začátku zpracování.
                             Slouží k výpočtu doby zpracování.

    Returns:
        None: Funkce nevrací žádnou hodnotu při úspěchu.

    Examples:
        >>> stats = {
        ...     'zpracovane_obce': 10,
        ...     'chyby': 0,
        ...     'celkem_volicu': 1000,
        ...     'celkem_platnych_hlasu': 800
        ... }
        >>> vypis_statistiky(stats, time.time() - 65)
        Souhrn zpracování:
        ------------------
        Doba zpracování: 1 minuta a 5 sekund
        Zpracováno obcí: 10
        Počet chyb: 0
        Celkový počet voličů: 1,000
        Celkový počet platných hlasů: 800
        Průměrná volební účast: 80.00%

    Notes:
        Funkce zobrazuje:
        - Doba zpracování ve formátu "x minut(y) a y sekund(y)".
        - Počet zpracovaných obcí.
        - Počet chyb, které nastaly při zpracování.
        - Celkový počet voličů a platných hlasů s formátováním čísel.
        - Vypočítanou průměrnou volební účast jako procento.

    """
    # Výpis statistik na konci
    cas_konce = time.time()
    celkovy_cas_zpracovani = cas_konce - cas_zacatku
    minuty = int(celkovy_cas_zpracovani // 60)
    sekundy = int(celkovy_cas_zpracovani % 60)

    cas_text = []
    if minuty > 0:
        cas_text.append(
            f"{minuty} " +
            ('minuta' if minuty == 1 else
            'minuty' if 1 < minuty < 5 else 'minut')
        )
    # Přidej sekundy vždy, když jsou > 0 nebo když nemáme minuty
    if sekundy > 0 or not cas_text:
        cas_text.append(
            f"{sekundy} " +
            ('sekunda' if sekundy == 1 else
            'sekundy' if 1 < sekundy < 5 else 'sekund')
        )

    cas_string = " a ".join(cas_text)

    volebni_ucast = 0
    if stats['celkem_volicu'] > 0:
    
        volebni_ucast = (
            stats['celkem_platnych_hlasu']/stats['celkem_volicu']*100
        )
        
    print(
        Fore.LIGHTCYAN_EX + MSG_STATISTICS.format(
            time=cas_string,
            pocet=stats['zpracovane_obce'],
            chyby=stats['chyby'],
            volici=stats['celkem_volicu'],
            hlasy=stats['celkem_platnych_hlasu'],
            ucast=round(volebni_ucast, 2)
        )
    )


def zpracuj_data() -> None:
    """
    Hlavní funkce pro zpracování volebních dat. 
    Řídí celý proces včetně:
    - kontroly vstupních argumentů
    - získání seznamu obcí
    - zpracování dat jednotlivých obcí
    - uložení výsledků do formátu CSV, JSON nebo XML
    - výpisu statistik zpracování
    Funkce automaticky zavolá další podfunkce pro kontrolu 
    argumentů, získání dat z webu, jejich zpracování, 
    uložení do souboru a zobrazení souhrnných statistik. 
    Pokud dojde k chybě, bude vypsána chybová zpráva a 
    program se ukončí s příslušným kódem.

    Args:
        None: Funkce nevyžaduje žádné argumenty.

    Returns:
        None: Funkce nevrací žádnou hodnotu při úspěchu.

    Raises:
        SystemExit: Při kritické chybě během zpracování
                    (např. při nesprávném počtu argumentů, neplatná URL,
                    nenalezená data obcí, chyba při parsování dat).
       
        Exception: Při neočekávané chybě během procesu.
        
        NoDataFoundError: Specifická výjimka, která je zaznamenána v logu,
                zpracována a poté se ukončí program s chybovým hlášením.
        
        DataParsingError: Specifická výjimka, která je zaznamenána v logu,
                zpracována a poté se ukončí program s chybovým hlášením.
    Examples:
        python election_scraper.py "https://volby.cz/pls/..." "vysledky.csv"

    Notes:
        Tento skript očekává dva argumenty příkazové řádky:
        - URL adresa okresu obsahující volební data.
        - Název výstupního souboru (včetně přípony), do kterého
          budou uloženy výsledky (CSV, JSON, XML).

        Po úspěšném provedení skript vypíše statistiky, včetně:
        - doby zpracování,
        - počtu zpracovaných obcí,
        - počtu chyb,
        - celkového počtu voličů,
        - celkového počtu platných hlasů,
        - průměrné volební účasti.
    """
    
    try:
        # Přidáme měření času
        cas_zacatku = time.time()        
        
        # Kontrola vstupních argumentů
        url_okresu, vystupni_soubor = zkontroluj_vstupy()

        # Získání seznamu obcí
        obce = ziskej_obce(url_okresu)

        # Zpracování obcí
        vysledky, stats = zpracuj_obce(obce)

        # Uložení do CSV/JSON/XML souboru
        uloz_vysledky(vysledky, vystupni_soubor)

        # Výpis statistik
        vypis_statistiky(stats, cas_zacatku)

    except SystemExit as e:
        # SystemExit je vyvolána našimi funkcemi při kritických chybách
        logging.info(LOG_INFO_PROGRAM_EXIT.format(exit_code=e.code))
        pass #sys.exit() byl vyvolán dříve
   
    except NoDataFoundError as e:
        # Zde zachytíme NoDataFoundError vyvolanou výše
        logging.error(LOG_ERROR_DATA_FAILED.format(error_detail=e))
        sys.exit(1)
        # Zde zachytíme DataParsingError vyvolanou výše
    
    except DataParsingError as e:
        logging.error(LOG_ERROR_PARSING_DATA.format(error_detail=e))
        sys.exit(1)
    
    except FileSavingError as e:
        # Zde zachytíme FileSavingError vyvolanou výše
        logging.error(LOG_ERROR_SAVING_FAILED, e)
        sys.exit(1)
    
    except UnsupportedFormatError as e:
        # Zde zachytíme UnsupportedFormatError vyvolanou výše
        logging.error(
            LOG_ERROR_UNSUPPORTED_FORMAT_FAILED.format(error_detail=e)
        )
        sys.exit(1)
    
    except Exception as e:
        logging.critical(
            LOG_CRITICAL.format(error_detail=e), exc_info=True
        )
        print("\n" + SEPARATOR)
        print(Fore.LIGHTYELLOW_EX + MSG_CRITICAL.format(error_detail=e))
        print(SEPARATOR + "\n")
        sys.exit(1)


if __name__ == "__main__":
    # Nastavení logování
    nastav_logovani(verbose = False, log_path='logs/volby_scraper.log')
    # Spuštění hlavní logiky
    zpracuj_data()

    




 

