import os
import re

# Fix ALL Python files to use proper relative/absolute imports
for root, dirs, files in os.walk('src'):
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root, file)
            with open(path, 'r') as f:
                content = f.read()
            
            new_content = content
            
            # Fix various import patterns
            fixes = [
                (r'^from config_loader ', 'from src.config_loader '),
                (r'^from trading\.', 'from src.trading.'),
                (r'^from utils\.', 'from src.utils.'),
                (r'^from risk_management\.', 'from src.risk_management.'),
                (r'^from monitoring\.', 'from src.monitoring.'),
                (r'^import config_loader', 'import src.config_loader'),
                (r'^import trading\.', 'import src.trading.'),
                (r'^import utils\.', 'import src.utils.'),
            ]
            
            for old, new in fixes:
                new_content = re.sub(old, new, new_content, flags=re.MULTILINE)
            
            if new_content != content:
                with open(path, 'w') as f:
                    f.write(new_content)
                print(f"Fixed: {path}")

print("Done!")
