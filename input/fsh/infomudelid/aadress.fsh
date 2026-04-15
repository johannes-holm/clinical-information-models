Logical: Aadress
Id: Aadress
Title: "Aadress"
Description: "Aadressi infomudel"

Characteristics: #can-be-target

* ^status = #draft
* ^publisher = "TEHIK"

* maakond 0..1 string "Maakond"
* asutusuksus 0..1 string "Asutusüksus"
* omavalitsus 0..1 string "Omavalitsus"
* postiindeks 0..1 integer "Postiindeks"
* korteriNumber 0..1 string "Korteri number"
* majaNumber 0..1 string "Maja number"
* tekst 0..1 string "Tekst"
* riik 0..1 code "Riik"
* riik from Riik (required)
* aadressiTuup 1..1 code "Aadressi tüüp"
* aadressiTuup from AadressiTuup (required)
* adsId 1..1 code "ADS ID"
* periood 0..1 Periood "Periood"