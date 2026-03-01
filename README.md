# Avtonomni Trgovalni Bot PowerSaver

**Profesionalni DeFi arbitražni sistem z AI in flash posojili**

---

## 📋 Kazalo

1. [Pregled sistema](#1-pregled-sistema)
2. [Namestitev](#2-namestitev)
3. [Konfiguracija](#3-konfiguracija)
4. [Zagon](#4-zagon)
5. [Testiranje na Sepolii](#5-testiranje-na-sepolii)
6. [Glavne funkcije](#6-glavne-funkcije)
7. [Nadzor in statistika](#7-nadzor-in-statistika)
8. [Varnost](#8-varnost)
9. [Odpravljanje težav](#9-odpravljanje-težav)
10. [Tehnična dokumentacija](#10-tehnična-dokumentacija)

---

## 1. Pregled sistema

### Kaj je PowerSaver?

PowerSaver je **avtonomni trgovalni bot** za Ethereum mainnet, ki samodejno išče in izvaja arbitražne priložnosti med različnimi Decentraliziranimi borzami (DEX).

### Ključne lastnosti

| Lastnost | Opis |
|----------|------|
| **Avtonomnost** | Deluje 24/7 brez posega uporabnika |
| **Flash posojila** | Avtomatsko zadolževanje za večje posle |
| **Multi-DEX** | Uniswap V2/V3, SushiSwap, Curve, Balancer |
| **AI strategije** | 15 različnih trgovalnih strategij |
| **Realni podatki** | Cene direktno iz blockchaina |
| **Flashbots** | Privatne transakcije |
| **Testnet** | Sepolia testnet za varno testiranje |

### Arhitektura

```
┌─────────────────────────────────────────────────────────────┐
│                    POWERSAVER BOT                           │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   │
│  │   Glavni     │   │  Trgovalni   │   │   Izvršilni │   │
│  │   vmesnik    │──▶│   motor      │──▶│   motor      │   │
│  └──────────────┘   └──────────────┘   └──────────────┘   │
│         │                  │                   │             │
│         ▼                  ▼                   ▼             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   │
│  │   Konfiguracija  │   │  Podatkovni   │   │   MEV        │   │
│  │   (config.json)  │   │   viri         │   │   Manager    │   │
│  └──────────────┘   └──────────────┘   └──────────────┘   │
│                                                    │         │
└────────────────────────────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────────┐
        │           BLOCKCHAIN LAYER             │
        │  Ethereum RPC │ Flashbots │ Subgraphs  │
        └────────────────────────────────────────┘
```

---

## 2. Namestitev

### Zahteve

- **Python 3.10+**
- **Linux/macOS/Windows (WSL)**
- **Ethereum node** (local ali RPC)
- **Ethereum wallet** s sredstvi

### Koraki namestitve

```bash
# 1. Kloniraj projekt
git clone https://github.com/DanyHacking/PowerSaver.git
cd PowerSaver

# 2. Namesti odvisnosti
pip install -r requirements.txt

# 3. Namesti Foundry (za smart contracts)
curl -L https://foundry.paradigm.xyz | bash
foundryup

# 4. Namesti Reth (opcijsko - najhitrejši node)
# Ali uporabi zunanji RPC (Infura/Alchemy)
```

---

## 3. Konfiguracija

### 3.1 Okoljske spremenljivke

```bash
# Kopiraj primer konfiguracije
cp .env.example .env
```

#### Glavne nastavitve (.env):

```bash
# ========================
# IZBERI OMREŽJE
# ========================

# Mainnet (produkcija)
USE_LOCAL_NODE=true        # Ali false za zunanji RPC

# Testnet (za testiranje)
# Uporabi --network sepolia pri zagonu

# ========================
# BLOCKCHAIN
# ========================

# RPC URL (local node ali Infura/Alchemy)
ETHEREUM_RPC_URL=http://localhost:8545
# Zunanji RPC: https://mainnet.infura.io/v3/YOUR_KEY

# ID verige (1 = Ethereum mainnet)
CHAIN_ID=1

# ========================
# DENARNICA
# ========================

# Privatni ključ (NIKOLI ne deli!)
TRADING_WALLET_PRIVATE_KEY=0x...

# Naslov denarnice
TRADING_WALLET_ADDRESS=0x...

# ========================
# AAVEE V3
# ========================

AAVE_V3_POOL_ADDRESS=0x87870Bca3F3fD6335C3F4ce6260135144110A857
```

### 3.2 Trgovalne nastavitve (config.json)

```json
{
    "trading": {
        "loan_amount": 75000,
        "max_loan_amount": 750000,
        "min_profit_threshold": 200,
        "max_concurrent_trades": 15,
        "max_slippage": 0.01,
        "scan_interval_seconds": 0.5
    },
    "tokens": ["ETH", "WETH", "USDC", "USDT", "DAI", "WBTC", "LINK", "UNI", "AAVE", "CRV", "SUSHI", "SNX", "COMP", "MKR", "MATIC", "LDO", "OP", "ARB", "STETH", "RETH", "GMX", "RNDR"],
    "exchanges": ["uniswap_v3", "uniswap_v2", "sushiswap", "curve", "balancer"],
    "mev": {
        "flashbots_enabled": true,
        "bundle_submission_interval_ms": 100
    }
}
```

### 3.3 Testnet nastavitve (.env.testnet)

```bash
# Kopiraj testnet primer
cp .env.testnet.example .env.testnet

# Uredi z testnimi podatki
TESTNET=true
SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/YOUR_KEY
TEST_TRADING_WALLET_PRIVATE_KEY=0x...
TEST_LOAN_AMOUNT=100
TEST_MIN_PROFIT=1
```

---

## 4. Zagon

### 4.1 Zagon na Mainnetu (Produkcija)

```bash
# Samo zagon
./start.sh

# Ali ročno
python3 -m src.main --network mainnet
```

### 4.2 Zagon na Testnetu (Sepolia)

```bash
# Preveri stanje denarnice
./start_testnet.sh --check

# Simulacija (brez resničnih transakcij)
./start_testnet.sh --dry

# Resnično testiranje
./start_testnet.sh

# Ali direktno
python3 -m src.main --network sepolia --dry-run
```

### 4.3 Zagon z lokalnim Reth vozliščem

```bash
# Samo zažene local node in trading
./start.sh
```

---

## 5. Testiranje na Sepolii

### Koraki pred mainnet zagonom:

1. **Pridobi testna sredstva:**
   - ETH: https://sepoliafaucet.com
   - USDC: https://app.sepolia.org/faucet

2. **Nastavi testnet konfiguracijo:**
   ```bash
   cp .env.testnet.example .env.testnet
   # Uredi .env.testnet
   ```

3. **Preveri sredstva:**
   ```bash
   ./start_testnet.sh --check
   ```

4. **Zaženi dry-run:**
   ```bash
   python3 -m src.main --network sepolia --dry-run
   ```

5. **Zaženi live test:**
   ```bash
   python3 -m src.main --network sepolia
   ```

6. **Spremljaj rezultate** in prilagodi nastavitve

---

## 6. Glavne funkcije

### 6.1 Avtonomno delovanje

Bot deluje **popolnoma avtonomno**:

```python
# Samodejno:
# - Skenira priložnosti
# - Izračunava dobiček
# - Izvršuje posle
# - Upravlja tveganja
# - Prilagaja zneske
# - Optimizira plin
```

### 6.2 Trgovalne strategije

| Strategija | Opis | Tveganje |
|------------|------|----------|
| Arbitraža | Izkoriščanje cenovnih razlik | Nizko |
| Triangularna | 3-smerna menjava | Nizko |
| Momentum | Sledenje trendom | Srednje |
| Volatilnost | Izkoriščanje volatilnosti | Srednje |
| MEV | Maximal Extractable Value | Nizko |
| Likvidacija | Avtomatske likvidacije | Srednje |

### 6.3 Podatkovni viri

- **Cene:** Uniswap V2/V3 (on-chain)
- **Likvidnost:** Direktno iz poolov
- **Provizije:** Fee tiers (300/3000 bps)
- **Gas:** Real-time iz RPC
- **Likvidacije:** Aave/Compound subgraphs

### 6.4 Podatki za vsak swap

Vsak swap vsebuje:

```python
{
    "path": ["ETH", "USDC", "DAI"],      # Pot tokenov
    "amount_in": 75000,                   # Vhodni znesek
    "amount_out": 75200,                   # Pričakovan izhod
    "min_out": 74448,                      # Min izhod (s slippage)
    "pool_addresses": ["0x...", "0x..."], # Naslovi poolov
    "pool_liquidities": [1200000, 800000], # Likvidnost v USD
    "fee_tiers": [3000, 300],              # Provizije v bps
    "token_addresses": ["0x...", "0x..."], # ERC20 naslovi
    "net_profit": 150,                     # Čisti dobiček
    "confidence": 0.85                      # Zaupanje (0-1)
}
```

---

## 7. Nadzor in statistika

### 7.1 Sledenje v realnem času

```python
from src.trading.aggressive_trading import AggressiveTradingBot

# Initialize
config = {...}
bot = AggressiveTradingBot(config)

# Pridobi statistiko
stats = bot.get_stats()
print(f"Skupni dobiček: ${stats['total_profit']}")
print(f"Število poslov: {stats['trades_executed']}")
print(f"Uspešnost: {stats['success_rate']}%")
```

### 7.2 Dashboard

```bash
# Odpri dashboard
python3 -c "
from src.main import AutonomousTradingSystemManager
manager = AutonomousTradingSystemManager()
manager.initialize_system()
print(manager.get_dashboard())
"
```

### 7.3 Logging

```bash
# Pregled zadnjih transakcij
tail -f logs/trading.log
```

---

## 8. Varnost

### ⚠️ Kritična opozorila

1. **Nikoli ne deli privatnega ključa!**
2. **Začni z majhnimi zneski!** ($100-500)
3. **Testiraj na Sepolii pred mainnetom!**
4. **Uporabi hardware wallet!** za velike zneske

### 8.1 Varnostni ukrepi

- [x] Profit threshold ($200 minimum)
- [x] Max slippage (1%)
- [x] Max concurrent trades (15)
- [x] Emergency pause
- [x] Flashbots (private transactions)
- [x] Gas optimization

### 8.2 Emergency ukrepi

```bash
# Zaustavi trading
EMERGENCY_PAUSE=true ./start.sh

# Ali pritisni Ctrl+C
```

---

## 9. Odpravljanje težav

### Pogoste težave

| Težava | Rešitev |
|--------|---------|
| "Connection refused" | Preveri RPC URL |
| "Insufficient funds" | Preveri ETH/USDC balance |
| "Execution reverted" | Preveri approval-je |
| "Gas too low" | Povečaj max_gas_price |
| "No opportunities" | Normalno - ni vedno priložnosti |

### Debugiranje

```bash
# Verbose logging
export LOG_LEVEL=DEBUG
python3 -m src.main --network mainnet

# Samo ena strategija
python3 -c "
import asyncio
from src.trading.aggressive_trading import AggressiveTradingBot

async def test():
    bot = AggressiveTradingBot({...})
    opportunities = await bot.scan_arbitrage_opportunities()
    print(opportunities)

asyncio.run(test())
"
```

---

## 10. Tehnična dokumentacija

### 10.1 Struktura projekta

```
PowerSaver/
├── src/
│   ├── main.py                 # Glavni vmesnik
│   ├── config.py               # Konfiguracija
│   ├── config_loader.py        # Nalagalnik configa
│   ├── trading/
│   │   ├── aggressive_trading.py  # Glavni trgovalni motor
│   │   ├── complete_trading_engine.py
│   │   └── trading_engine.py
│   ├── utils/
│   │   ├── swap_data.py        # Podatki o swapih
│   │   ├── network_selector.py # Izbira omrežja
│   │   ├── execution_engine.py # Izvrševanje
│   │   ├── mev_manager.py      # MEV/Flashbots
│   │   ├── advanced_data_feed.py
│   │   └── profit_verifier.py
│   ├── monitoring/
│   │   └── monitor.py
│   └── risk_management/
│       └── risk_manager.py
├── config.json                 # Trgovalne nastavitve
├── config_networks.json        # Omrežja
├── start.sh                   # Mainnet zagon
├── start_testnet.sh           # Testnet zagon
├── .env.example               # Primer .env
└── .env.testnet.example       # Primer testnet .env
```

### 10.2 Pomembni naslovi (Mainnet)

| Kontrakt | Naslov |
|----------|--------|
| Uniswap V3 Factory | `0x1F98431c8aD98523631AE4a59f267346ea31F984` |
| Uniswap V2 Factory | `0x5C69bEe701ef814a2B6fe3cF77eE1eD5e2b3f2c4` |
| Aave V3 Pool | `0x87870Bca3F3fD6335C3F4ce6260135144110A857` |
| WETH | `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2` |
| USDC | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` |

### 10.3 API Reference

#### Glavni razredi:

```python
# AggressiveTradingBot
bot = AggressiveTradingBot(config)
opportunities = await bot.scan_arbitrage_opportunities()
result = await bot.execute_trade(signal)

# NetworkSelector
selector = NetworkSelector()
config = selector.get_config()  # mainnet ali testnet

# SwapDataBuilder
builder = create_swap_builder()
swap = await builder.build_swap_route(...)
```

---

## 📞 Podpora

- **GitHub Issues:** https://github.com/DanyHacking/PowerSaver/issues
- **Dokumentacija:** V projektu

---

## 📄 Licenca

MIT License

---

**⚠️ OPOZORILO:** Ta software je namenjen izobraževalnim namenom. Uporaba na realnem mainnetu je na lastno odgovornost. Vedno testirajte na testnetu preden uporabite realna sredstva.
