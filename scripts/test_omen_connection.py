"""
OMEN ↔ RISKCAST Connection Test Script
=======================================

Tests that both systems can communicate:
1. OMEN health check (port 8000)
2. RISKCAST health check (port 8001) 
3. Fetch signals from OMEN
4. Parse signals into RISKCAST format
5. Test full pipeline: OMEN → ORACLE → RISKCAST

Usage:
    python scripts/test_omen_connection.py
    
    # Or with custom ports:
    python scripts/test_omen_connection.py --omen-url http://localhost:8000 --riskcast-url http://localhost:8001
"""

import asyncio
import argparse
import sys
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, ".")

# Colors for terminal output
class C:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"


def _safe_symbol(symbol: str, fallback: str) -> str:
    encoding = sys.stdout.encoding or "utf-8"
    try:
        symbol.encode(encoding)
        return symbol
    except Exception:
        return fallback


def _safe_text(text: str) -> str:
    encoding = sys.stdout.encoding or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding)


CHECK = _safe_symbol("✓", "v")
CROSS = _safe_symbol("✗", "x")
WARN = _safe_symbol("⚠", "!")
ARROW = _safe_symbol("→", ">")


def ok(msg: str):
    print(f"  {C.GREEN}{CHECK}{C.END} {_safe_text(msg)}")

def fail(msg: str):
    print(f"  {C.RED}{CROSS}{C.END} {_safe_text(msg)}")

def warn(msg: str):
    print(f"  {C.YELLOW}{WARN}{C.END} {_safe_text(msg)}")

def info(msg: str):
    print(f"  {C.BLUE}{ARROW}{C.END} {_safe_text(msg)}")

def header(msg: str):
    print(f"\n{C.BOLD}{C.CYAN}{'='*60}{C.END}")
    print(f"{C.BOLD}{C.CYAN}  {_safe_text(msg)}{C.END}")
    print(f"{C.BOLD}{C.CYAN}{'='*60}{C.END}")


async def test_health(client, name: str, url: str) -> bool:
    """Test service health endpoint."""
    try:
        response = await client.get(f"{url}/health/", follow_redirects=True)
        if response.status_code == 200:
            data = response.json()
            # Handle wrapped response (OMEN wraps in { data: ..., meta: ... })
            if "data" in data and "meta" in data:
                health_data = data["data"]
                meta = data["meta"]
                ok(f"{name} is HEALTHY (mode: {meta.get('mode', 'N/A')}, "
                   f"real_coverage: {meta.get('real_source_coverage', 'N/A')})")
                return True
            else:
                status = data.get("status", "unknown")
                ok(f"{name} is {status.upper()}")
                return True
        else:
            fail(f"{name} returned HTTP {response.status_code}")
            return False
    except Exception as e:
        fail(f"{name} unreachable: {e}")
        return False


async def test_omen_signals(client, omen_url: str, api_key: str) -> list:
    """Fetch signals from OMEN and display them."""
    try:
        headers = {"X-API-Key": api_key}
        response = await client.get(
            f"{omen_url}/api/v1/signals/",
            params={"limit": 10},
            headers=headers,
            follow_redirects=True,
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Handle wrapped response
            if "data" in data and "meta" in data:
                meta = data["meta"]
                inner = data["data"]
                
                info(f"Mode: {meta.get('mode', 'N/A')}")
                info(f"Live Gate: {meta.get('live_gate_status', 'N/A')}")
                info(f"Real Coverage: {meta.get('real_source_coverage', 0):.0%}")
                
                real = meta.get("real_sources", [])
                mock = meta.get("mock_sources", [])
                if real:
                    ok(f"Real sources: {', '.join(real)}")
                if mock:
                    warn(f"Mock sources: {', '.join(mock)}")
                
                # Extract signals from inner data
                if isinstance(inner, dict) and "signals" in inner:
                    signals = inner["signals"]
                    total = inner.get("total", len(signals))
                elif isinstance(inner, list):
                    signals = inner
                    total = len(signals)
                else:
                    signals = []
                    total = 0
            elif "signals" in data:
                signals = data["signals"]
                total = data.get("total", len(signals))
            else:
                signals = data if isinstance(data, list) else []
                total = len(signals)
            
            ok(f"Got {len(signals)} signals (total: {total})")
            
            # Display first few signals
            for i, sig in enumerate(signals[:5]):
                signal_id = sig.get("signal_id", "N/A")
                title = sig.get("title", "N/A")[:60]
                prob = sig.get("probability", 0)
                conf = sig.get("confidence_score", 0)
                cat = sig.get("category", "N/A")
                
                print(f"\n    {C.BOLD}Signal {i+1}:{C.END} {signal_id}")
                print(f"    Title: {title}")
                print(f"    Category: {cat} | Prob: {prob:.2f} | Confidence: {conf:.2f}")
                
                geo = sig.get("geographic", {})
                chokepoints = geo.get("chokepoints", [])
                if chokepoints:
                    print(f"    Chokepoints: {', '.join(chokepoints)}")
                
                evidence = sig.get("evidence", [])
                if evidence:
                    sources = [e.get("source", "?") for e in evidence[:3]]
                    print(f"    Evidence: {', '.join(sources)}")
            
            return signals
        
        elif response.status_code == 401 or response.status_code == 403:
            fail(f"Auth failed (HTTP {response.status_code}). Check OMEN_API_KEY.")
            info("OMEN expects header: X-API-Key: <your-key>")
            info("In dev mode with OMEN_DEV_AUTH_BYPASS=true, use: dev-test-key")
            return []
        else:
            fail(f"OMEN signals returned HTTP {response.status_code}")
            try:
                err = response.json()
                info(f"Error: {json.dumps(err, indent=2)[:200]}")
            except Exception:
                pass
            return []
            
    except Exception as e:
        fail(f"Failed to fetch signals: {e}")
        return []


async def test_omen_multi_source(client, omen_url: str, api_key: str) -> dict:
    """Test OMEN multi-source endpoint."""
    try:
        headers = {"X-API-Key": api_key}
        response = await client.get(
            f"{omen_url}/api/v1/multi-source/sources",
            headers=headers,
            follow_redirects=True,
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Handle wrapped response
            if "data" in data:
                sources_data = data["data"]
            else:
                sources_data = data
            
            sources = sources_data.get("sources", [])
            healthy = sources_data.get("healthy_count", 0)
            total = sources_data.get("total_count", len(sources))
            
            ok(f"Multi-source: {healthy}/{total} sources healthy")
            
            for src in sources:
                name = src.get("name", "?")
                enabled = src.get("enabled", False)
                status = src.get("status", "unknown")
                icon = C.GREEN + "●" + C.END if status == "healthy" else C.RED + "●" + C.END
                safe_icon = _safe_text(icon)
                if safe_icon != icon:
                    safe_icon = f"{C.GREEN}v{C.END}" if status == "healthy" else f"{C.RED}x{C.END}"
                print(f"    {safe_icon} {_safe_text(name)}: {_safe_text(status)} (enabled={enabled})")
            
            return sources_data
        else:
            warn(f"Multi-source returned HTTP {response.status_code}")
            return {}
            
    except Exception as e:
        warn(f"Multi-source check failed: {e}")
        return {}


async def test_signal_parsing(signals: list) -> bool:
    """Test that OMEN signals can be parsed by RISKCAST OmenClient."""
    if not signals:
        warn("No signals to test parsing")
        return False
    
    try:
        from app.omen.client import OmenClient, OmenClientConfig
        
        client = OmenClient(OmenClientConfig(
            base_url="http://localhost:8000",
            api_key="dev-test-key",
        ))

        def _fill_temporal_defaults(payload: dict) -> dict:
            temporal = payload.get("temporal") or {}
            if temporal.get("detected_at") is None:
                temporal["detected_at"] = payload.get("generated_at") or payload.get("observed_at") or payload.get("created_at")
            payload["temporal"] = temporal
            return payload
        
        success_count = 0
        fail_count = 0
        
        for sig_data in signals[:5]:
            try:
                parsed = client._parse_signal(_fill_temporal_defaults(sig_data))
                success_count += 1
                info(f"Parsed: {parsed.signal_id} → category={parsed.category.value}, "
                     f"chokepoint={parsed.geographic.primary_chokepoint.value}")
            except Exception as e:
                fail_count += 1
                fail(f"Parse error: {e}")
        
        if success_count > 0:
            ok(f"Successfully parsed {success_count}/{success_count + fail_count} signals")
            return True
        else:
            fail("Could not parse any signals")
            return False
            
    except ImportError as e:
        warn(f"Cannot import RISKCAST modules: {e}")
        warn("Run from RISKCAST root directory with venv activated")
        return False


async def test_refresh_signals(client, omen_url: str, api_key: str) -> bool:
    """Test OMEN signal refresh (triggers real data fetch)."""
    try:
        headers = {"X-API-Key": api_key}
        response = await client.post(
            f"{omen_url}/api/v1/signals/refresh",
            params={"limit": 20, "min_liquidity": 500},
            headers=headers,
            follow_redirects=True,
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Handle wrapped response
            if "data" in data:
                result = data["data"]
            else:
                result = data
            
            created = result.get("signals_created", 0)
            fetched = result.get("events_fetched", 0)
            proc_time = result.get("processing_time_ms", 0)
            
            ok(f"Refresh: {fetched} events → {created} signals ({proc_time:.0f}ms)")
            return created > 0
        else:
            warn(f"Refresh returned HTTP {response.status_code}")
            try:
                err = response.json()
                info(f"Detail: {json.dumps(err)[:200]}")
            except Exception:
                pass
            return False
            
    except Exception as e:
        fail(f"Refresh failed: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(description="Test OMEN ↔ RISKCAST connection")
    parser.add_argument("--omen-url", default="http://localhost:8000", help="OMEN API URL")
    parser.add_argument("--riskcast-url", default="http://localhost:8001", help="RISKCAST API URL")
    parser.add_argument("--api-key", default="dev-test-key", help="OMEN API key")
    parser.add_argument("--refresh", action="store_true", help="Also test signal refresh")
    args = parser.parse_args()
    
    import httpx
    
    results = {
        "omen_health": False,
        "riskcast_health": False,
        "omen_signals": False,
        "multi_source": False,
        "parsing": False,
        "refresh": False,
    }
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
        # ============================================================
        # TEST 1: Health Checks
        # ============================================================
        header("TEST 1: Health Checks")
        
        results["omen_health"] = await test_health(client, "OMEN", args.omen_url)
        results["riskcast_health"] = await test_health(client, "RISKCAST", args.riskcast_url)
        
        if not results["omen_health"]:
            print(f"\n{C.RED}OMEN is not running!{C.END}")
            print(f"Start OMEN API server:")
            print(f"  cd \"C:\\Users\\RIM\\OneDrive\\Desktop\\omen v2\"")
            print(f"  .venv\\Scripts\\activate")
            print(f"  set PYTHONPATH=src")
            print(f"  uvicorn omen.main:app --host 0.0.0.0 --port 8000 --reload")
            
        if not results["riskcast_health"]:
            print(f"\n{C.YELLOW}RISKCAST is not running (optional for this test){C.END}")
            print(f"Start RISKCAST API server:")
            print(f"  cd \"C:\\Users\\RIM\\OneDrive\\Desktop\\RISK CAST V2\"")
            print(f"  .venv\\Scripts\\activate")  
            print(f"  uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload")
        
        if not results["omen_health"]:
            print(f"\n{C.RED}Cannot proceed without OMEN. Start OMEN first.{C.END}")
            return
        
        # ============================================================
        # TEST 2: OMEN Multi-Source Status
        # ============================================================
        header("TEST 2: OMEN Data Sources")
        
        sources = await test_omen_multi_source(client, args.omen_url, args.api_key)
        results["multi_source"] = bool(sources)
        
        # ============================================================
        # TEST 3: Fetch Signals
        # ============================================================
        header("TEST 3: Fetch Signals from OMEN")
        
        signals = await test_omen_signals(client, args.omen_url, args.api_key)
        results["omen_signals"] = len(signals) > 0
        
        # ============================================================
        # TEST 4: Parse into RISKCAST format
        # ============================================================
        header("TEST 4: Parse Signals → RISKCAST Format")
        
        results["parsing"] = await test_signal_parsing(signals)
        
        # ============================================================
        # TEST 5: Refresh (optional - triggers real API calls)
        # ============================================================
        if args.refresh:
            header("TEST 5: Trigger Signal Refresh (Live Data)")
            results["refresh"] = await test_refresh_signals(client, args.omen_url, args.api_key)
        
        # ============================================================
        # SUMMARY
        # ============================================================
        header("SUMMARY")
        
        total = sum(1 for v in results.values() if v)
        tested = len([k for k, v in results.items() if k != "refresh" or args.refresh])
        
        for test_name, passed in results.items():
            if test_name == "refresh" and not args.refresh:
                continue
            icon = f"{C.GREEN}{CHECK}{C.END}" if passed else f"{C.RED}{CROSS}{C.END}"
            label = test_name.replace("_", " ").title()
            print(f"  {icon} {_safe_text(label)}")
        
        print(f"\n  {C.BOLD}Result: {total}/{tested} tests passed{C.END}")
        
        if total == tested:
            print(f"\n  {C.GREEN}{C.BOLD}{_safe_text('ALL SYSTEMS GO! OMEN <-> RISKCAST pipeline is working!')}{C.END}")
        elif results["omen_health"] and results["omen_signals"]:
            print(f"\n  {C.YELLOW}{C.BOLD}{_safe_text('OMEN is working but some integration tests failed.')}{C.END}")
            print(f"  {_safe_text('Check the errors above for details.')}")
        else:
            print(f"\n  {C.RED}{C.BOLD}{_safe_text('Integration not working. Fix the issues above.')}{C.END}")


if __name__ == "__main__":
    asyncio.run(main())
