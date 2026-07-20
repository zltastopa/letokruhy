# Letokruhy

Vekové zloženie Národnej rady SR naprieč všetkými deviatimi volebnými
obdobiami (1994 až 2023), poskladané "from first principles" z verejných
stránok NRSR: z rodných dátumov samotných poslancov.

Ako letokruhy stromu prezrádzajú jeho vek, tieto dáta ukazujú, ako starne
slovenský parlament.

**Live:** https://letokruhy.zltastopa.sk

## Čo v tom nájdeš

Jedna samostatná stránka [`index.html`](index.html) (bez externých závislostí,
otvorí sa aj offline) so štyrmi pohľadmi:

- **Interaktívne porovnanie dvoch rokov:** dvoma jazdcami vyber ľubovoľné dva
  roky od 1994 po dnešok (predvolene 1994 vs aktuálny rok). Pre každý rok sa
  vezme parlament, ktorý v tom roku úradoval, a vek poslancov sa prepočíta k
  danému roku (aktuálny rok k dnešnému dňu, ostatné k polovici roka). Zoskupené
  päťročné kategórie, os X aj Y sa prispôsobia, tlačidlo na výmenu, a po nájazde
  myšou tooltip s podielom aj absolútnym počtom poslancov.
- **Krabicové grafy pre každé obdobie:** celý rozptyl veku (min, Q1, medián,
  Q3, max, priemer) plus každý poslanec ako bodka.
- **Trend v čase:** priemerný a mediánový vek za 30 rokov.
- **Zloženie vekových skupín:** stopercentný podiel skupín pod 30, 30s, 40s,
  50s a 60+.
- **Kopírovať / stiahnuť PNG:** každý graf sa dá jedným klikom skopírovať do
  schránky alebo stiahnuť ako PNG, s odkazom `letokruhy.zltastopa.sk`
  vygenerovaným priamo v obrázku.

Hlavné zistenie: priemerný vek parlamentu je pozoruhodne stabilný (okolo 47
rokov) počas troch dekád, s miernym nárastom na 48,4 v roku 2023. Podiel
šesťdesiatnikov a starších sa zhruba zdvojnásobil (z 9 % na 18 %).

## Odkiaľ sú dáta

Pre každé obdobie `t` (1 až 9):

1. **Zoznam poslancov:** `sid=poslanci/zoznam_abc&CisObdobia=t` vráti každé
   `PoslanecID`, ktoré v danom období slúžilo (historické stránky sú kumulatívne,
   vrátane náhradníkov).
2. **Detail poslanca:** `sid=poslanci/poslanec&PoslanecID=<id>&CisObdobia=t`
   vráti dátum narodenia (`Narodený(á)`), stranu (`Kandidoval(a) za`), meno,
   národnosť.

**Vek** = celé roky ku dňu volieb daného obdobia. Opravy a doplnenia:

- Zoznam pre aktuálne obdobie (2023) uvádza len sediacich poslancov, preto je
  doplnený o všetkých, ktorí v ňom hlasovali (`data/extra_ids.json`), čím sa
  zachytia aj tí, čo mandát opustili počas obdobia (napr. ministri). Spolu 189.
- Traja poslanci mali na nrsr.sk chybný alebo prázdny dátum narodenia (Sólymos,
  Jurinová, Borguľa). Opravené podľa Wikipédie a TASR (viď `BIRTH_OVERRIDE`
  v `scripts/build.py`).

## Obmedzenia

- **Aktuálne obdobie:** zoznam pre prebiehajúce obdobie ukazuje len sediacich
  poslancov. Tých, čo mandát opustili počas obdobia, dopĺňa `data/extra_ids.json`.
  Kým sa obdobie neskončí, nových odídencov treba do tohto súboru doplniť ručne
  (po voľbách sa zoznam obdobia stane kumulatívnym a súbor je už zbytočný).
- **Reprodukovateľnosť:** surové HTML (`cache/`) je gitignored a dá sa kedykoľvek
  znova stiahnuť cez `scrape.py`. Auditovateľným zdrojom pravdy je commitnutý
  `data/mps.csv` (dátum narodenia a strana pre každého poslanca). Keďže nrsr.sk
  sa môže meniť, presná historická reprodukcia závisí od aktuálneho stavu zdroja.
- **Kvalita zdroja:** `build.py` sa preruší, ak niektoré obdobie vráti menej ako
  140 poslancov alebo ak chýba viac než 5 dátumov narodenia, aby sa nepublikoval
  neúplný dataset.

## Ako je to zostavené

```
scripts/scrape.py   # stiahne zoznamy + detaily poslancov do cache/ (idempotentné)
scripts/build.py    # parsuje -> data/mps.csv + data/distribution.json
scripts/render.py   # -> index.html
```

Skripty používajú iba štandardnú knižnicu Pythonu 3.12 (žiadne závislosti).

```bash
python scripts/scrape.py
python scripts/build.py
python scripts/render.py
```

## Nasadenie

- **GitHub Actions** zostavujú a nasadzujú stránku (`.github/workflows/deploy.yml`):
  pri každom pushi do `main` sa spustí `render.py` a výsledok sa publikuje na
  GitHub Pages.
- **Obnova dát** (`.github/workflows/refresh.yml`): raz mesačne (a na požiadanie)
  znova stiahne dáta z NRSR, prebuduje `data/` a commitne zmeny, čo spustí
  nasadenie.
- Vlastná doména je nastavená cez súbor `CNAME` (`letokruhy.zltastopa.sk`).
  V nastaveniach DNS stačí nasmerovať CNAME záznam na GitHub Pages.

## Súbory

- `index.html` - samostatná stránka (dáta sú vložené priamo v nej).
- `data/mps.csv` - jeden riadok na (obdobie, poslanec): meno, strana, dátum
  narodenia, vek pri voľbách.
- `data/distribution.json` - vek a súhrnná štatistika za každé obdobie.
- `data/extra_ids.json` - doplnené `PoslanecID` pre obdobie 9.
- `cache/` - surové HTML (gitignored, regenerovateľné cez `scrape.py`).

## Súvisiace

- [zltastopa.sk](https://zltastopa.sk/) - domovská stránka Žltá Stopa
- [nrsr-dochadzka](https://github.com/zltastopa/nrsr-dochadzka) - dochádzka a
  hlasovania NR SR

Súčasť projektu **Žltá Stopa**. Licencia MIT.
