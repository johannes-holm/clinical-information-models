Logical: Nimi
Id: Nimi
Title: "Nimi"
Description: "Nime infomudel"

Characteristics: #can-be-target

* ^status = #draft
* ^publisher = "TEHIK"

* eesnimi 0..1 string "Eesnimi"
* perekonnanimi 0..1 string "Perekonnanimi"
* tekst 0..1 string "Tekst"
* tiitel 0..1 string "Tiitel"
* kasutus 1..1 code "Kasutus"
* kasutus from NameUse (required)
* periood 0..1 Periood "Periood"

