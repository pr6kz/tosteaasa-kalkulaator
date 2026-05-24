# Tõsteaasa kalkulaator

Veebirakendus on koostatud lõputöö **„Silevardast tõsteaasade kandevõime
hindamine raudbetoonist seinaelementide pööramisel“** põhjal.

Autor: **Martin Bergmann**

Rakendus on kasutatav Streamlitis:

👉 [Ava tõsteaasa kalkulaator](https://tosteaasa-kalkulaator.streamlit.app/)

## Seos lõputööga

Rakendus aitab töös
esitatud valemeid kasutada ja visualiseerida ning näitab, kuidas elemendi
geomeetria, tõsteaasade paigutus, trossi geomeetria ja tõsteaasa parameetrid
mõjutavad tõsteaasade kasutusastet raudbetoonelemendi pööramisel kahe kraana abil.

Rakendus kuvab muu hulgas:

- lubatud elemendi kaalu vormist vabastamisel, tõstmisel ja pööramisel;
- tõsteaasade kasutusastet pöördenurga funktsioonina;
- tõsteaasadele mõjuvaid jõukomponente;
- elemendi pööramise animatsiooni.

## Arvutusmudeli ulatus

Rakendus arvutab painutatud tõsteaasade kontrollid kolmes olukorras:

- elemendi vormist vabastamine;
- elemendi tõstmine;
- elemendi pööramine kahe kraana abil.

Arvutus põhineb lõputöös toodud valemitel:

- koormused: valemid 3.1-3.4;
- tõsteaasa terase kandevõime ja vähendustegurid: valemid 4.3-4.8;
- elemendi lubatav kaal: valemid 4.10-4.12;
- kasutusaste: valemid 4.13-4.14;
- pööramise geomeetria ja vähendustegurid: valemid 5.62, 5.64, 5.85,
  5.87 ja 5.94-5.101.

## Projekti struktuur

- `streamlit_app.py` - Streamliti veebirakendus.
- `lifting_loops/` - arvutusmoodulid, sisendmudelid, valikuloogika ja tabeliandmed.
- `tests/` - automaattestid arvutusloogika kontrollimiseks.
- `pyproject.toml` - projekti sõltuvused ja CLI käivituskirje.

Rakenduse lähtekood on avaldatud GPL3 litsentsi all.
