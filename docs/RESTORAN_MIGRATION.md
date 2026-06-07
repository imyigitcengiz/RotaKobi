# BiDoluPos → CoolOPS restoran migrasyonu

> **Dal:** `restoran-pos` · **Stabil taban:** tag `v1-kobi-stable` (`main`)

Yeni repo açılmaz. Canlı deploy `main` dalından devam eder; restoran işi bu dalda yapılır.

## Kurallar

1. `main` — yalnızca KOBİ/saha servis düzeltmeleri (canlı).
2. `restoran-pos` — BiDoluPos'tan taşınan tüm restoran kodu.
3. `BiDoluPos/` — yerel referans (git'e eklenmez); silme checklist tamamlanana kadar tutulur.
4. Mevcut KOBİ modülleri kapatılmaz; restoran `vertical=restaurant` paketi ile ayrılır.

## Taşınma sırası (BiDoluPos referans)

| Faz | BiDoluPos kaynağı | CoolOPS hedefi | Durum |
|-----|-------------------|----------------|-------|
| 0 | — | Tag + dal + `restaurant` app iskeleti | ✅ |
| 1 | `Category`, `MenuItem` | `RestaurantCategory`, `RestaurantMenuItem` + UI | 🔄 iskelet |
| 2 | `Table` | `RestaurantTable` + salon ekranı | 🔄 iskelet |
| 3 | `Order`, `OrderItem` | Sipariş modelleri + adisyon | ⏳ |
| 4 | `Kitchen` view | Mutfak kuyruğu | ⏳ |
| 5 | `CashRegister`, ödeme | Kasa + muhasebe bağlantısı | ⏳ |
| 6 | `FranchisePortal` | Bayi paneli (`BusinessBrand` dealer) | ⏳ |
| 7 | `OfficialWebsite` | Website / QR menü | ⏳ |
| 8 | Stripe / iyzico | Plan ödeme (platform) | ⏳ |

## BiDoluPos silme checklist

- [ ] Masa + sipariş + mutfak CoolOPS'ta çalışıyor
- [ ] Restoran vertical testleri geçiyor
- [ ] `restoran-pos` → `main` merge + deploy
- [ ] Yerel `BiDoluPos/` klasörü silindi
- [ ] `bidolu-pos` GitHub repo archive

## Geri dönüş

```bash
git checkout main
git checkout v1-kobi-stable -- .   # acil geri alma (dikkatli kullan)
```

## Deploy

Dokploy şimdilik **`main`** branch. Restoran hazır olunca `restoran-pos` merge edilir; merge öncesi staging isteğe bağlı.
