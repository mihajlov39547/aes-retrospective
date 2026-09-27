# Bibliografski dnevnik

Početna provera: 2026-09-27. Ovo nije sistematski pregled literature niti potvrda svih tvrdnji o stanju u 2026. Za svaki konačni nalaz sačuvati tačan odeljak/stranicu i datum provere. Ne koristiti današnje izdanje kao dokaz onoga što je bilo poznato 2003.

## Uneti izvori

- `fips46-3`: [primarni izvor](https://csrc.nist.gov/pubs/fips/46-3/final).
- `fips197-2001`: [primarni izvor](https://csrc.nist.gov/pubs/fips/197/final-(1)).
- `fips197-2023`: [primarni izvor](https://csrc.nist.gov/pubs/fips/197/final).
- `nist-aes-report-2001`: [primarni izvor](https://nvlpubs.nist.gov/nistpubs/jres/106/3/j63nec.pdf).
- `rijndael-proposal-1999`: [primarni izvor](https://cs.ru.nl/~joan/papers/JDA_VRI_Rijndael_V2_1999.pdf).
- `sp800-67r2`: [primarni izvor](https://csrc.nist.gov/pubs/sp/800/67/r2/final).
- `des-withdrawal-2005`: [primarni izvor](https://csrc.nist.gov/news/2005/withdrawal-of-fips-46-3-fips-74-and-fips-81).
- `tdea-withdrawal-2023`: [primarni izvor](https://www.nist.gov/news-events/news/2023/06/nist-withdraw-special-publication-800-67-revision-2).
- `sp800-38a`: [primarni izvor](https://csrc.nist.gov/pubs/sp/800/38/a/final).
- `sp800-38d`: [primarni izvor](https://csrc.nist.gov/pubs/sp/800/38/d/final).
- `rfc4106`: [primarni izvor](https://www.rfc-editor.org/rfc/rfc4106.html).
- `rfc8446`: [primarni izvor](https://www.rfc-editor.org/info/rfc8446/).

FIPS 197 (2001) i ažuriranje (2023) su odvojeni zapisi. Povlačenje starog izdanja ne znači povlačenje AES algoritma. SP 800-67 Rev. 2 ima označen status povučenog dokumenta. Obaveštenje o TDEA iz 2023. i statusna stranica dokumenta imaju različite uloge.

RFC Editor stranica RFC 8446 pri proveri navodi RFC 9846 kao naslednika: https://www.rfc-editor.org/info/rfc9846/ . RFC 8446 je unet kao istorijski izvor. Pre pisanja savremenog TLS odeljka proveriti tačan datum, metapodatke, promene i primenljivost naslednika na vremenski presek rada. SP 800-38A i 38D stranice najavljuju revizije; proveriti nova izdanja pred završetak rada.

## Literatura za proveru

- TODO: verify reference for Shannon, Communication Theory of Secrecy Systems, kao izvor konfuzije i difuzije.
- TODO: verify reference for original DES standard (1977), istoriju dizajna i originalne radove o diferencijalnoj/linearnoj kriptoanalizi.
- TODO: verify reference for EFF Deep Crack i distributed.net DES izazove, sa datumima i uslovima merenja.
- TODO: verify reference for meet-in-the-middle, sigurnost dvoključnog i troključnog TDEA i uslove napada.
- TODO: verify reference for Sweet32, originalni rad i konkretne protokolske pretpostavke.
- TODO: verify reference for AES biclique cryptanalysis, related-key napade i reduced-round rezultate; proveriti autore, model, složenosti i publikaciju.
- TODO: verify reference for Bernstein cache-timing rad i Osvik/Shamir/Tromer radove o cache napadima, sa tačnim verzijama.
- TODO: verify reference for Intel AES-NI dokumentaciju, akademske analize constant-time implementacija i ARM crypto extensions.
- TODO: verify reference for RFC 9846 i aktuelne preporuke TLS/IPsec do datuma preseka; RFC errata i status proveravati odvojeno od prvobitnog teksta.
- TODO: verify reference for IEEE 802.11 CCMP/GCMP i WPA2/WPA3 profile iz primarnih IEEE/Wi-Fi Alliance dokumenata.
- TODO: verify reference for 3GPP EEA2/NEA2/EIA2/NIA2, tačan TS, release, funkciju i obaveznost podrške.
- TODO: verify reference for IEEE MACsec, optičke sisteme i implementacije mrežne opreme sa AES akceleracijom.
- TODO: verify reference for merenu zastupljenost AES-128/192/256; standardizacija nije dokaz tržišnog udela.
- TODO: verify reference for Groverov originalni rad i procene fault-tolerant quantum resursa za AES.
- TODO: verify reference for aktuelne NIST preporuke o simetričnim ključevima u postkvantnom kontekstu.
- TODO: verify reference for Ascon/lightweight NIST standard i njegov tačan obim; ne izvoditi zaključak o univerzalnoj zameni AES-a.
- TODO: verify reference for retrospektivne diskusije o AES-192, block size i key schedule iz primarnih ili recenziranih izvora.
- TODO: verify reference for starost svemira samo ako se uvede ta edukativna skala; nije potrebna za osnovnu ekstrapolaciju.

## Pravila evidencije

Za svaki nalaz voditi: tvrdnja, izvor i verzija, odeljak/stranica, model napada ili profil protokola, datum provere, ograničenje zaključka. DOI/ISBN i stranice uneti samo kada su provereni. Blogovi i forumi mogu predložiti pitanje, ali ne zamenjuju dokaz. Neslaganja izvora beležiti otvoreno. Tek nakon provere dodati BibLaTeX zapis i postojeći ključ u poglavlje.
