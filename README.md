# 📊 Web Scraper pro získání volebních výsledků

Tento Pythonový skript slouží k automatizovanému stažení a zpracování volebních dat 
ze zadané webové stránky 
(například https://www.volby.cz/pls/ps2017nss/ps32?xjazyk=CZ&xkraj=14&xnumnuts=8103). 
Pomocí knihovny BeautifulSoup provádí parsování HTML obsahu 
a ukládá strukturovaná data do formátu JSON (případně CSV).
Projekt je určen jako ukázka praktického použití Pythonu pro web scraping, 
datové zpracování a práci se soubory. Kód je přehledně rozdělen do modulárních funkcí 
a obsahuje rozšířené logování a ošetření výjimek.

---

## 🔧 Hlavní funkce
- 📥 Stažení HTML obsahu z veřejných webových stránek
- 🔍 Parsování obsahu pomocí knihovny BeautifulSoup
- 🧹 Zpracování a extrakce relevantních údajů (např. výsledky voleb, počty hlasů)
- 💾 Uložení výstupu do formátu JSON nebo CSV
- 🛡 Robustní ošetření chyb a výjimek (včetně vlastních výjimek)
- 📝 Barevný výstup pro přehlednější CLI komunikaci
- 🐍 Dobře strukturovaný kód vhodný pro rozšíření a testování

## 🗂 Struktura projektu
Projekt se skládá z následujících částí:
- main.py – hlavní skript pro spuštění programu
- ukazky/ – složka pro výstupní soubory
- requirements.txt – seznam potřebných knihoven

---

## ▶️ Jak spustit
Doporučuji vytvořit si virtuální prostředí:
```bash
python -m venv venv

source venv/bin/activate  # na UNIX

\venv\Scripts\activate # na Windows
```

Nainstaluj závislosti:
```bash
pip install -r requirements.txt
```

Spusť hlavní skript (přes příkazovou řádku):

Příklad:
```bash
python main.py "https://www.volby.cz/pls/ps2017nss/ps32?xjazyk=CZ&xkraj=14&xnumnuts=8103" "karvina.csv"
```

---

## 💻 Ukázka výstupu

Při běhu programu je uživatel informován o průběhu:
```
🔍 Probíhá validace URL: https://www.volby.cz/pls/ps2017nss/ps32?xjazyk=CZ&xkraj=14&xnumnuts=8103
📋 Získávám seznam obcí z adresy...
🔄 Zpracovávám volební data pro jednotlivé obce...
🔄 Celkový počet obcí ke zpracování: 17
💾 Ukládám výsledky do souboru 'karvina.csv' ve formátu CSV...
✅ HOTOVO! Výsledky byly úspěšně uloženy do 'karvina.csv'.
```
 ![Ukázka běhu](ukazky/Ukazka%20prubehu.gif)

Výstupní CSV soubor vypadá takto:

Číslo obce,Název obce,Voliči,Vydané obálky,Platné hlasy,Občanská demokratická strana,Řád národa - Vlastenecká unie,CESTA ODPOVĚDNÉ SPOLEČNOSTI,Česká str.sociálně demokrat.,Radostné Česko,STAROSTOVÉ A NEZÁVISLÍ,Komunistická str.Čech a Moravy,Strana zelených,"ROZUMNÍ-stop migraci,diktát.EU",Strana svobodných občanů,Blok proti islam.-Obran.domova,Občanská demokratická aliance,Česká pirátská strana,Česká národní fronta,Referendum o Evropské unii,TOP 09,ANO 2011,Dobrá volba 2016,SPR-Republ.str.Čsl. M.Sládka,Křesť.demokr.unie-Čs.str.lid.,Česká strana národně sociální,REALISTÉ,SPORTOVCI,Dělnic.str.sociální spravedl.,Svob.a př.dem.-T.Okamura (SPD),Strana Práv Občanů
598925,Albrechtice,3173,1957,1944,109,4,2,181,2,131,211,15,22,12,1,3,139,0,5,25,635,1,1,174,0,10,1,0,255,5
599051,Bohumín,17613,9040,8973,579,12,4,1241,9,133,821,85,91,87,7,6,641,0,12,119,3157,18,33,305,3,55,14,25,1478,38

<img src="ukazky/soubor_v_csv.png" alt="CSV" width="400"/>


Výstupní JSON soubor vypadá takto:

```json
[
  {
    "Číslo obce": "598925",
    "Název obce": "Albrechtice",
    "Voliči": 3173,
    "Vydané obálky": 1957,
    "Platné hlasy": 1944,
    "Občanská demokratická strana": 109,
    "Řád národa - Vlastenecká unie": 4,
    
  },
  ...
]
```

<img src="ukazky/soubor_v_json.png" alt="JSON" width="200"/>

Výstupní XML soubor vypadá takto:

```
<?xml version='1.0' encoding='utf-8'?>
<vysledky>
  <obec>
    <Číslo obce>598925</Číslo obce>
    <Název obce>Albrechtice</Název obce>
    <Voliči>3173</Voliči>
    <Vydané obálky>1957</Vydané obálky>
    <Platné hlasy>1944</Platné hlasy>
    <Občanská demokratická strana>109</Občanská demokratická strana>
    <Řád národa - Vlastenecká unie>4</Řád národa - Vlastenecká unie>
    <CESTA ODPOVĚDNÉ SPOLEČNOSTI>2</CESTA ODPOVĚDNÉ SPOLEČNOSTI>
</obec>
```
<img src="ukazky/soubor_v_xml.png" alt="XML" width="300"/>
---

## 📦 Závislosti
Projekt využívá tyto externí knihovny:

- requests
- beautifulsoup4
- colorama (barevný výstup do terminálu)

Všechny závislosti jsou uvedeny v requirements.txt.

---

## 📁 Uložené soubory

Výsledky se ukládají do výstupního souboru dle volby uživatele jako:
- CSV soubor (např. vysledky.csv)
- JSON soubor (např. vysledky.json)
- XML souboru (např. výsledky.xml)

---

## ❗ Ošetření chyb
Program zachytává tyto typy chyb:
- Chyby při stahování stránky (např. špatná URL, timeout)
- Chyby při parsování HTML (nevalidní struktura)
- Chyby při zápisu na disk (např. nemám oprávnění)
- Nečekané chyby – jsou zalogovány a bezpečně ohlášeny uživateli a zároveň uložené do log souboru

Používají se vlastní výjimky pro lepší správu chyb:
- FileSavingError při ukládání,
- DataParsingError při parsování  HTML,
- NoDataFoundError při nenalezení žádných dat,
- UnsupportedFormatError při zadání chybného formátu souboru.

---

## 🧠 Motivace a cíl
Tento projekt vznikl jako součást mého studia Pythonu. Cílem bylo:
- Naučit se pracovat s reálnými daty z webu,
- Získat praktické zkušenosti s knihovnami jako BeautifulSoup, requests,
- Vyzkoušet si psaní robustního a opakovaně použitelného kódu,
- Zdokumentovat projekt pro prezentaci znalostí (např. při hledání zaměstnání).

---

## 📬 Kontakt
Pokud máš otázky nebo zpětnou vazbu:
📧 l.krcmarikova@seznam.cz 

---

📌 Poznámka:
Tento skript není určen pro masové stahování dat. Prosím, respektuj pravidla webu, 
ze kterého data čerpáš (robots.txt, fair use).


