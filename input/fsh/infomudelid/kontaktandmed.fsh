Logical: Kontaktandmed
Id: Kontaktandmed
Title: "Kontaktandmed"
Description: "Kontaktandmete infomudel"

Characteristics: #can-be-target

* ^status = #draft
* ^publisher = "TEHIK"

* eMail 0..* BackboneElement "E-mail"
  * meiliaadress 1..1 string "Meiliaadress"
  * periood 0..1 Periood "Periood"
  * meiliaadressTuup 1..1 code "Meiliaadress tüüp"
* telefon 0..* BackboneElement "Telefon"
  * telefoninumber 1..1 string "Telefoninumber"
  * periood 0..1 Periood "Periood"
  * telefoniTuup 1..1 code "Telefoni tüüp"