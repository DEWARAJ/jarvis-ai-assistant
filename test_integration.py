"""Test JARVIS integration with Hermes Agent and Firecrawl."""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_env_keys():
    """Verify all API keys are set."""
    from dotenv import load_dotenv
    load_dotenv()
    
    keys = {
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
        "FIRECRAWL_API_KEY": os.getenv("FIRECRAWL_API_KEY", "")
    }
    
    print("=== API Keys Status ===")
    for key, value in keys.items():
        status = "✓ SET" if value else "✗ MISSING"
        masked = value[:10] + "..." + value[-4:] if len(value) > 14 else value
        print(f"{key:20} {status:10} {masked if value else ''}")
    
    all_set = all(keys.values())
    print(f"\nAll keys configured: {'YES' if all_set else 'NO'}")
    return all_set


def test_hermes_tool():
    """Test Hermes Agent integration."""
    print("\n=== Testing Hermes Tool ===")
    try:
        from tools.hermes_tool import HermesTool
        hermes = HermesTool()
        
        # Check if Hermes is installed
        d, py = hermes._resolve()
        if d and py:
            print(f"✓ Hermes Agent found at: {d}")
            print(f"✓ Python executable: {py}")
            
            # Quick test (without actually calling it to avoid tokens)
            print("✓ HermesTool loaded successfully")
            return True
        else:
            print("✗ Hermes Agent not found")
            print(f"  Expected location: {hermes._resolve()[0] or 'Not detected'}")
            return False
    except Exception as e:
        print(f"✗ Hermes Tool error: {e}")
        return False


def test_firecrawl_tool():
    """Test Firecrawl integration."""
    print("\n=== Testing Firecrawl Tool ===")
    try:
        from tools.firecrawl_tool import FirecrawlTool
        firecrawl = FirecrawlTool()
        
        ready, msg = firecrawl._check_ready()
        if ready:
            print("✓ Firecrawl Tool ready")
            print(f"✓ API base: {firecrawl.base_url}")
            return True
        else:
            print(f"✗ Firecrawl not ready: {msg}")
            return False
    except Exception as e:
        print(f"✗ Firecrawl Tool error: {e}")
        return False


def test_tool_registry():
    """Test that tools are properly registered."""
    print("\n=== Testing Tool Registry ===")
    try:
        from core.tool_registry import ToolRegistry
        
        # Mock context for testing
        context = {}
        registry = ToolRegistry("config/tools.json", context=context, logger=None)
        
        tools = registry.names()
        print(f"✓ Loaded {len(tools)} tools")
        
        # Check key tools
        required = ["hermes", "firecrawl", "web"]
        for tool in required:
            if tool in tools:
                print(f"  ✓ {tool}")
            else:
                print(f"  ✗ {tool} MISSING")
        
        # Test tool instantiation
        hermes_tool = registry.get("hermes")
        firecrawl_tool = registry.get("firecrawl")
        
        if hermes_tool:
            print("✓ Hermes tool instantiated")
        if firecrawl_tool:
            print("✓ Firecrawl tool instantiated")
        
        return bool(hermes_tool and firecrawl_tool)
    except Exception as e:
        print(f"✗ Tool Registry error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_hermes_config():
    """Test Hermes Agent configuration."""
    print("\n=== Testing Hermes Agent Config ===")
    hermes_home = os.path.expanduser("~/AppData/Local/hermes")
    
    config_path = os.path.join(hermes_home, "config.yaml")
    env_path = os.path.join(hermes_home, ".env")
    
    if os.path.exists(config_path):
        print(f"✓ Config found: {config_path}")
    else:
        print(f"✗ Config missing: {config_path}")
    
    if os.path.exists(env_path):
        print(f"✓ .env found: {env_path}")
        
        # Check keys in Hermes .env
        try:
            with open(env_path, 'r') as f:
                content = f.read()
                for key in ["ANTHROPIC_API_KEY", "GEMINI_API_KEY", "FIRECRAWL_API_KEY"]:
                    if key in content:
                        print(f"  ✓ {key} present")
                    else:
                        print(f"  ✗ {key} missing")
        except Exception as e:
            print(f"  Error reading .env: {e}")
    else:
        print(f"✗ .env missing: {env_path}")
    
    return os.path.exists(config_path) and os.path.exists(env_path)


def main():
    """Run all integration tests."""
    print("╔════════════════════════════════════════════════════╗")
    print("║  JARVIS Integration Test Suite                    ║")
    print("║  Hermes Agent + Firecrawl + API Keys              ║")
    print("╚════════════════════════════════════════════════════╝\n")
    
    results = []
    
    # Test 1: Environment keys
    results.append(("API Keys", test_env_keys()))
    
    # Test 2: Hermes config
    results.append(("Hermes Config", test_hermes_config()))
    
    # Test 3: Hermes tool
    results.append(("Hermes Tool", test_hermes_tool()))
    
    # Test 4: Firecrawl tool
    results.append(("Firecrawl Tool", test_firecrawl_tool()))
    
    # Test 5: Tool registry
    results.append(("Tool Registry", test_tool_registry()))
    
    # Summary
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name:20} {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All integrations working! JARVIS is ready.")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed. Check output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
