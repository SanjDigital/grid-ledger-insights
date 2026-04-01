"""
Test that the syntax fix worked
"""
with open("syntax_check.log", "w", encoding='utf-8') as f:
    try:
        import backend.revenue_engine
        f.write("OK: revenue_engine module imported successfully\n")
        print("SUCCESS")
    except SyntaxError as e:
        f.write(f"SYNTAX ERROR: {e}\n")
        print(f"SYNTAX ERROR: {e}")
    except Exception as e:
        f.write(f"ERROR: {type(e).__name__}: {e}\n")
        print(f"ERROR: {type(e).__name__}: {e}")
