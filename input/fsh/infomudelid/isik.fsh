Logical: Isik
Id: Isik
Title: "Isik"
Description: "Isiku infomudel"

Characteristics: #can-be-target

* ^status = #draft
* ^publisher = "TEHIK"

* kontaktandmed 0..* Kontaktandmed "Isiku kontaktandmed"
* aadress 0..* Aadress "Isiku aadress"
* nimi 0..* Nimi "Isiku nimi"
* periood 0..1 Periood "Kaua on olnud kontaktisik"
* suhtlusKeel 0..* code "Isiku suhtluskeel"
* seotus 1..* code "Kuidas on inimesega seotud"
* identifikaator 0..* id "Isiku identifikaator"
