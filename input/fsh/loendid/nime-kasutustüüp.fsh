ValueSet: NameUse
Id: name-use
Title: "Nime kasutustüüp"
* ^status = #draft
* include codes from system NameUseSystem

CodeSystem: NameUseSystem
Id: name-use-system
Title: "FHIR nime kasutustüüpide koodisüsteem"
* ^status = #draft
* ^caseSensitive = true
* #usual "Usual" "Tavaline"
* #official "Official" "Ametlik"
* #temp "Temp" "Ajutine"
* #nickname "Nickname" "Hüüdnimi"
* #anonymous "Anonymous" "Anonüümne"
* #old "Old" "Vana"
* #maiden "Name changed for Marriage" "Neiupõlvenimi"