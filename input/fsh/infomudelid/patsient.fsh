Logical: Patsient
Id: Patsient
Title: "Patsient"
Description: "Patsiendi infomudel"

Characteristics: #can-be-target

* ^status = #draft
* ^publisher = "TEHIK"

* identifikaator 1..* id "Patsiendi identifikaator"
* sunniaeg 0..1 date "Patsiendi sünniaeg"
* sugu 0..1 code "Patsiendi sugu"
* surmaFakt 0..1 boolean "Surma fakt"
* suhtluskeel 0..* code "Patsiendi suhtluskeel"
* nimi 0..* Nimi "Patsiendi nimi"
* aadress 0..* Aadress "Patsiendi aadress"
* kontaktandmed 0..* Kontaktandmed "Patsiendi kontaktandmed"
* kontaktisik 0..* Isik "Patsiendi kontaktisik/seotud isik"