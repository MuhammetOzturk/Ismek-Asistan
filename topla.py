#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ENSTİTÜ İSTANBUL (İSMEK) aktif eğitim toplayıcı — portalın PageMethods JSON API'siyle.

Akış (2026-09-04 canlı doğrulanmış):
  1. POST /enstitu_egitimler.aspx/Programlar            -> portalın aktif program kartları
  2. POST /egitim_detay.aspx/egitim_detay_ver           -> programın statik içeriği (amaç, ön koşul, sınav, malzeme)
  3. POST /egitim_detay.aspx/egitim_merkezleri_list     -> merkezler + kurslar (tarih, kontenjan, kayıt durumu)

Çıktılar: veri/kayitlar/{id}.json, veri/markdown/{id}.md,
          veri/aktif_egitimler.json (bütünleşik), veri/ozet.json (koşum istatistiği).

Naziklik: istekler arası gecikme + üstel geri çekilme + oturum yenileme; devam edebilir (var olan kayıtları atlar).
"""
import argparse
import datetime as dt
import json
import re
import sys
import time
from pathlib import Path

import requests

BASE = "https://enstitu.ibb.istanbul/portal/"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
KOK = Path(__file__).resolve().parent
VERI = KOK / "veri"
KAYIT = VERI / "kayitlar"
MD = VERI / "markdown"

PROGRAMLAR = dict(
    egitim_tipi_combo="-1", egitim_dili_combo="-1", egitim_dali_combo="-1",
    egitim_alani_combo="-1", programlar_combo="-1", lokasyon_combo="-1",
    zaman_liste_combo="-1", kayit_durumu="-1", kayida_acilacaklar="-1",
    egitim_merkezi="-1", belge="-1",
)


def oturum():
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept-Language": "tr,tr;q=0.9,en;q=0.5",
        "Content-Type": "application/json; charset=utf-8",
    })
    for _ in range(3):  # site arada bağlantıyı resetliyor: çerez ısınması da dayanıklı olmalı
        try:
            s.get(BASE + "egitimler.aspx", timeout=45)
            break
        except requests.RequestException:
            time.sleep(3)
    return s


def istek(s, yol, govde, deneme=4):
    """Sayfa arada bağlantıyı resetliyor: deneme + geri çekilme + oturum yenileme."""
    global SESS
    for i in range(deneme):
        try:
            r = s.post(yol, json=govde, timeout=45, headers={"Referer": referer_of(yol)})
            if r.status_code == 200:
                return r
        except requests.RequestException:
            pass
        time.sleep(2 + 2 * i)
        s = oturum()
        SESS = s
    return None


def referer_of(yol):
    sayfa = yol.split("/")[4].split("/")[0]
    return BASE + sayfa


def tarihi_ayikla(deger):
    """'/Date(1789938000000)/' -> '2026-10-21 14:00' (Europe/Istanbul, +3 sabit)."""
    m = re.match(r"/Date\((-?\d+)\)/", str(deger or ""))
    if not m:
        return deger
    ms = int(m.group(1))
    d = dt.datetime(1970, 1, 1) + dt.timedelta(milliseconds=ms) + dt.timedelta(hours=3)
    return d.strftime("%Y-%m-%d %H:%M")


def ad_parcayla(brans_adi):
    """'Mesleki İngilizce (Alan/Dal)' -> (ad, alan, dal)"""
    m = re.match(r"^(?P<ad>.+?)\s*\((?P<alan>[^/()]+?)(?:/(?P<dal>[^/()]+?))?\)\s*$", brans_adi or "")
    if not m:
        return brans_adi, None, None
    return m["ad"].strip(), ((m["alan"] or "").strip() or None), ((m["dal"] or "").strip() or None)


def programlar_cek(s):
    r = istek(s, BASE + "enstitu_egitimler.aspx/Programlar", PROGRAMLAR)
    if not r:
        sys.exit("Programlar listesi alınamadı")
    kartlar = r.json()["d"]
    print(f"[katalog] {len(kartlar)} aktif program kartı alındı", flush=True)
    return kartlar


def detay_cek(s, brans):
    r = istek(s, BASE + "egitim_detay.aspx/egitim_detay_ver",
              {"BransCode": brans, "EgitimVSID": 0, "EgitiminVerilisSekli": ""})
    if not r:
        return None
    try:
        d = r.json()["d"]
        return d[0] if d else None
    except (ValueError, KeyError, IndexError):
        return None


def merkezler_cek(s, brans):
    r = istek(s, BASE + "egitim_detay.aspx/egitim_merkezleri_list",
              {"egitim_": "hepsi", "Ilce": "-1", "kyt_drm": "-1", "mrk_drm": "-1", "BransCode": brans})
    if not r:
        return None
    try:
        return r.json()["d"]
    except (ValueError, KeyError):
        return None


def kayit_uret(kart, detay, merkezler, cekim_ts):
    ad, alan, dal = ad_parcayla(detay.get("bransAdi") or kart.get("ProgramAdi"))
    kurslar = []
    kart_sekil = (kart.get("EgitimVerilisSekli") or kart.get("egitim_tipi") or "")
    sekil = {p.strip() for p in kart_sekil.split(",") if p.strip()}
    for mrk in merkezler or []:
        for k in mrk.get("Kurslar_Sonuc") or []:
            sekil.add(k.get("EgitimVerilisSekli") or "")
            kurslar.append({
                "kurs_id": k.get("KursId"),
                "merkez_id": k.get("EgitimMerkeziId"),
                "merkez_adi": k.get("EgitimMerkeziAdi"),
                "ilce": (k.get("EgitimMerkeziAdi") or "").split(" / ")[-1].strip() or None,
                "verilis_sekli": k.get("EgitimVerilisSekli"),
                "egitim_dili": k.get("EgitimVerilisDili"),
                "baslangic": tarihi_ayikla(k.get("DersBaslamaTarihi")),
                "bitis": tarihi_ayikla(k.get("DersBitisTarihi")),
                "toplam_saat": k.get("ToplamDersSaati"),
                "haftalik_saat": k.get("HaftalikDersSaati"),
                "kontenjan": k.get("Kontenjan"),
                "basvuru_sayisi": k.get("ToplamBasvuru"),
                "kayit_durumu": k.get("OnlineKayitDurumuAdi") or None,
                "kayit_alma_durumu": k.get("KayitAlmaDurumu"),
                "kayit_acilis": tarihi_ayikla(k.get("KayitAlmaZamani")),
                "gunler": [
                    {"gun": g.get("GunAdi"), "baslangic": g.get("BaslangicSaati"),
                     "bitis": g.get("BitisSaati")}
                    for g in k.get("listKursGunleri") or []
                ],
            })
    kayit_say = {"acik": sum(1 for k in kurslar if k["kayit_alma_durumu"]),
                 "kapali": sum(1 for k in kurslar if not k["kayit_alma_durumu"])}
    return {
        "brans_code": int(kart["ProgramId"]),
        "program": {
            "ad": ad,
            "bolum": kart.get("bolum_adi"),
            "seviye": kart.get("egitim_katki_seviyesi"),
            "alan": alan,
            "dal": dal,
            "resim_url": kart.get("resim"),
            "belge_id": kart.get("belgeId"),
        },
        "sure_saat": int(kart["saat"]) if str(kart.get("saat") or "").isdigit() else None,
        "verilis_sekli": sorted(x for x in sekil if x),
        "icerik": {
            "amac": detay.get("egitimin_amaci"),
            "on_kosullar": detay.get("on_kosullar"),
            "sinav_bilgisi": detay.get("sinav_bilgisi"),
            "malzeme_ekipman": detay.get("malzeme_ekipman_bilgisi"),
            "yas_bilgisi": detay.get("yas_bilgisi"),
        },
        "kurslar": kurslar,
        "kayit_ozeti": kayit_say,
        "meta": {
            "kaynak_url": BASE + f"egitim_detay.aspx?BransCode={kart['ProgramId']}",
            "cekim_ts": cekim_ts,
        },
    }


def md_uret(k):
    satir = ["---"]
    for anahtar, deger in [
        ("brans_code", k["brans_code"]),
        ("program", k["program"]["ad"]),
        ("bolum", k["program"]["bolum"]),
        ("seviye", k["program"]["seviye"]),
        ("sure_saat", k["sure_saat"]),
        ("verilis_sekli", ", ".join(k["verilis_sekli"])),
        ("kayit_acik_kurs", k["kayit_ozeti"]["acik"]),
        ("kaynak_url", k["meta"]["kaynak_url"]),
        ("cekim_ts", k["meta"]["cekim_ts"]),
    ]:
        if isinstance(deger, str) and (", " in deger or ":" in deger):
            deger = f'"{deger}"'
        satir.append(f"{anahtar}: {deger if deger is not None else 'null'}")
    satir.append("---")
    icerik = k["icerik"]
    bolumler = [("Program", icerik.get("amac")), ("Eğitime Kabul Koşulları", icerik.get("on_kosullar")),
                ("Sınav Bilgisi", icerik.get("sinav_bilgisi")),
                ("Malzeme / Ekipman", icerik.get("malzeme_ekipman"))]
    for baslik, metin in bolumler:
        if metin:
            satir += ["", f"## {baslik}", "", metin.strip()]
    if k["kurslar"]:
        satir += ["", "## Planlanan Kurslar", "",
                  "| Merkez (İlçe) | Tarih | Günler / Saat | Toplam Saat | Kontenjan | Başvuru | Kayıt |",
                  "|---|---|---|---|---|---|---|"]
        for kurs in k["kurslar"]:
            gunler = ", ".join(f"{g['gun']} {g['baslangic']}-{g['bitis']}" for g in kurs["gunler"]) or "-"
            satir.append(f"| {kurs['merkez_adi']} ({kurs['ilce']}) "
                         f"| {kurs['baslangic']} → {kurs['bitis']} | {gunler} "
                         f"| {kurs['toplam_saat']} | {kurs['kontenjan']} | {kurs['basvuru_sayisi']} "
                         f"| {kurs['kayit_durumu']} |")
        satir += ["", f"_Kayıt durumları {k['meta']['cekim_ts']} çekimidir; güncel durum portaldan doğrulanmalı._"]
    return "\n".join(satir) + "\n"


def ozet_yaz(kayitlar, basladi, atlanan, hata_sayisi):
    acik = sum(k["kayit_ozeti"]["acik"] for k in kayitlar)
    kurslar = sum(len(k["kurslar"]) for k in kayitlar)
    merkezler = len({(k["brans_code"], c["merkez_id"]) for k in kayitlar for c in k["kurslar"]})
    ilceler = sorted({c["ilce"] for k in kayitlar for c in k["kurslar"] if c["ilce"]})
    ozet = {
        "koşum": {"baslangic": basladi, "bitis": dt.datetime.now().isoformat(timespec="seconds")},
        "program_sayisi": len(kayitlar),
        "atlanan_kayit": atlanan,
        "detay_hatasi": hata_sayisi,
        "kurs_sayisi": kurslar,
        "benzersiz_merkez": merkezler,
        "acik_kayit_kurs": acik,
        "ilce_sayisi": len(ilceler),
        "ilceler": ilceler,
    }
    (VERI / "ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=2), encoding="utf-8")
    return ozet


def main():
    global SESS
    ayristir = argparse.ArgumentParser(description="İSMEK aktif eğitim toplayıcı")
    ayristir.add_argument("--limit", type=int, default=0, help="yalnız ilk N program (deneme)")
    ayristir.add_argument("--delay", type=float, default=0.7, help="istekler arası bekleme (sn)")
    ayristir.add_argument("--sadece-katalog", action="store_true", help="detay çekmeden sadece kartlar")
    args = ayristir.parse_args()

    VERI.mkdir(exist_ok=True)
    KAYIT.mkdir(exist_ok=True)
    MD.mkdir(exist_ok=True)

    SESS = oturum()
    kartlar = programlar_cek(SESS)
    if args.sadece_katalog:
        (VERI / "katalog.json").write_text(
            json.dumps(kartlar, ensure_ascii=False, indent=2), encoding="utf-8")
        return
    if args.limit:
        kartlar = kartlar[:args.limit]

    basladi = dt.datetime.now().isoformat(timespec="seconds")
    kayitlar, atlanan, hata = [], 0, 0
    for i, kart in enumerate(kartlar, 1):
        bc = int(kart["ProgramId"])
        yol = KAYIT / f"{bc}.json"
        if yol.exists():
            kayitlar.append(json.loads(yol.read_text(encoding="utf-8")))
            atlanan += 1
            continue
        time.sleep(args.delay)
        detay = detay_cek(SESS, bc)
        time.sleep(args.delay)
        merkezler = merkezler_cek(SESS, bc)
        cekim = dt.datetime.now().isoformat(timespec="seconds")
        if detay is None and not merkezler:
            hata += 1
            print(f"[{i}/{len(kartlar)}] {bc} — detay + merkez boş (atlandı)", flush=True)
            continue
        k = kayit_uret(kart, detay or {}, merkezler, cekim)
        yol.write_text(json.dumps(k, ensure_ascii=False, indent=2), encoding="utf-8")
        (MD / f"{bc}.md").write_text(md_uret(k), encoding="utf-8")
        kayitlar.append(k)
        if i % 50 == 0 or i == len(kartlar):
            print(f"[{i}/{len(kartlar)}] işlendi | kurs: {sum(len(x['kurslar']) for x in kayitlar)} "
                  f"| hata: {hata}", flush=True)

    (VERI / "aktif_egitimler.json").write_text(
        json.dumps(kayitlar, ensure_ascii=False, indent=2), encoding="utf-8")
    ozet = ozet_yaz(kayitlar, basladi, atlanan, hata)
    print(json.dumps({x: ozet[x] for x in ["program_sayisi", "kurs_sayisi", "benzersiz_merkez",
                                           "acik_kayit_kurs", "ilce_sayisi", "detay_hatasi"]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())