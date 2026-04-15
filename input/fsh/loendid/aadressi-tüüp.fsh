ValueSet: AadressiTuup
Id: aadressi-tuup
Title: "Aadressi tüüp"
* ^status = #draft
* include codes from system AadressiTuupSystem

CodeSystem: AadressiTuupSystem
Id: aadressi-tuup-system
Title: "Aadressi tüüpide koodisüsteem"
* ^status = #draft
* ^caseSensitive = true
* #home "Home" "Kodu"
* #work "Work" "Töö"
* #temp "Temporary" "Ajutine"
* #old "Old/Incorrect" "Vana"
* #billing "Billing" "?"
