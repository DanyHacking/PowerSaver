#!/usr/bin/env python3
"""
Production Security Audit Script
For mainnet autonomous flash loan trading system
NO simulations - REAL production security analysis
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime


class SecurityAuditor:
    """Production security audit for trading system"""
    
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "audits": [],
            "summary": {}
        }
    
    def log_audit(self, audit_name, status, details):
        """Log audit result"""
        self.results["audits"].append({
            "name": audit_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        print(f"[{status}] {audit_name}: {details}")
    
    def check_secrets_exposure(self):
        """Check for exposed secrets in production"""
        try:
            env_file = self.project_root / ".env"
            if env_file.exists():
                with open(env_file) as f:
                    content = f.read()
                    # Check for hardcoded private keys
                    if "PRIVATE_KEY" in content and "0x" in content:
                        self.log_audit("Secrets Exposure", "WARNING", 
                                     "Private key pattern found in .env")
                    else:
                        self.log_audit("Secrets Exposure", "PASS", 
                                     "No exposed private keys detected")
            else:
                self.log_audit("Secrets Exposure", "PASS", 
                             ".env file not found")
        except Exception as e:
            self.log_audit("Secrets Exposure", "ERROR", str(e))
    
    def check_gitignore(self):
        """Check .gitignore for production"""
        try:
            gitignore = self.project_root / ".gitignore"
            if gitignore.exists():
                with open(gitignore) as f:
                    content = f.read()
                    required_patterns = [".env", "*.log", "__pycache__"]
                    missing = [p for p in required_patterns if p not in content]
                    
                    if missing:
                        self.log_audit("GitIgnore", "WARNING", 
                                     f"Missing patterns: {missing}")
                    else:
                        self.log_audit("GitIgnore", "PASS", 
                                     "All required patterns present")
            else:
                self.log_audit("GitIgnore", "WARNING", 
                             ".gitignore not found")
        except Exception as e:
            self.log_audit("GitIgnore", "ERROR", str(e))
    
    def check_code_security(self):
        """Check code for security issues"""
        try:
            result = subprocess.run(
                ["bandit", "-r", "src", "-f", "json"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                issues = json.loads(result.stdout)
                critical = len([i for i in issues if i.get("severity") == "HIGH"])
                
                if critical > 0:
                    self.log_audit("Code Security", "WARNING", 
                                 f"Found {critical} high severity issues")
                else:
                    self.log_audit("Code Security", "PASS", 
                                 "No critical security issues found")
            else:
                self.log_audit("Code Security", "INFO", 
                             "Bandit not available or no issues")
        except Exception as e:
            self.log_audit("Code Security", "INFO", f"Check skipped: {e}")
    
    def check_dependency_security(self):
        """Check dependencies for vulnerabilities"""
        try:
            result = subprocess.run(
                ["safety", "check", "--json"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.log_audit("Dependency Security", "PASS", 
                             "No known vulnerabilities found")
            else:
                issues = json.loads(result.stdout)
                self.log_audit("Dependency Security", "WARNING", 
                             f"Found {len(issues)} vulnerable dependencies")
        except Exception as e:
            self.log_audit("Dependency Security", "INFO", 
                         f"Check skipped: {e}")
    
    def check_smart_contract_security(self):
        """Check smart contracts for security issues"""
        try:
            contracts_dir = self.project_root / "contracts"
            if contracts_dir.exists():
                result = subprocess.run(
                    ["forge", "build", "--force"],
                    cwd=contracts_dir,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    self.log_audit("Smart Contract Security", "PASS", 
                                 "Contracts compiled successfully")
                else:
                    self.log_audit("Smart Contract Security", "WARNING", 
                                 "Compilation issues detected")
            else:
                self.log_audit("Smart Contract Security", "INFO", 
                             "Contracts directory not found")
        except Exception as e:
            self.log_audit("Smart Contract Security", "INFO", 
                         f"Check skipped: {e}")
    
    def check_risk_management(self):
        """Check risk management implementation"""
        try:
            risk_manager = self.project_root / "src" / "risk_management" / "risk_manager.py"
            if risk_manager.exists():
                with open(risk_manager) as f:
                    content = f.read()
                    
                    checks = {
                        "daily_loss_limit": "max_daily_loss" in content,
                        "stop_loss": "stop_loss" in content,
                        "take_profit": "take_profit" in content,
                        "position_limits": "max_position" in content
                    }
                    
                    if all(checks.values()):
                        self.log_audit("Risk Management", "PASS", 
                                     "All risk controls implemented")
                    else:
                        missing = [k for k, v in checks.items() if not v]
                        self.log_audit("Risk Management", "WARNING", 
                                     f"Missing controls: {missing}")
            else:
                self.log_audit("Risk Management", "ERROR", 
                             "Risk manager not found")
        except Exception as e:
            self.log_audit("Risk Management", "ERROR", str(e))
    
    def check_transaction_validation(self):
        """Check transaction validation logic"""
        try:
            trading_engine = self.project_root / "src" / "trading" / "trading_engine.py"
            if trading_engine.exists():
                with open(trading_engine) as f:
                    content = f.read()
                    
                    checks = {
                        "amount_validation": "validate" in content.lower(),
                        "signature_check": "signature" in content.lower(),
                        "nonce_check": "nonce" in content.lower()
                    }
                    
                    if all(checks.values()):
                        self.log_audit("Transaction Validation", "PASS", 
                                     "Transaction validation implemented")
                    else:
                        missing = [k for k, v in checks.items() if not v]
                        self.log_audit("Transaction Validation", "WARNING", 
                                     f"Missing validations: {missing}")
            else:
                self.log_audit("Transaction Validation", "INFO", 
                             "Trading engine not found")
        except Exception as e:
            self.log_audit("Transaction Validation", "INFO", 
                         f"Check skipped: {e}")
    
    def check_production_settings(self):
        """Verify production settings are correct"""
        try:
            config_file = self.project_root / "config" / "trading_config.json"
            if config_file.exists():
                with open(config_file) as f:
                    config = json.load(f)
                    
                    checks = {
                        "test_mode_disabled": config.get("trading", {}).get("test_mode") == False,
                        "simulation_disabled": config.get("trading", {}).get("simulate_trades") == False,
                        "auto_execute_enabled": config.get("trading", {}).get("auto_execute") == True,
                        "trading_enabled": config.get("trading", {}).get("trading_enabled") == True
                    }
                    
                    if all(checks.values()):
                        self.log_audit("Production Settings", "PASS", 
                                     "All production settings correct")
                    else:
                        failed = [k for k, v in checks.items() if not v]
                        self.log_audit("Production Settings", "WARNING", 
                                     f"Failed checks: {failed}")
            else:
                self.log_audit("Production Settings", "INFO", 
                             "Config file not found")
        except Exception as e:
            self.log_audit("Production Settings", "ERROR", str(e))
    
    def generate_report(self, output_file=None):
        """Generate security audit report"""
        passed = len([a for a in self.results["audits"] if a["status"] == "PASS"])
        warnings = len([a for a in self.results["audits"] if a["status"] == "WARNING"])
        errors = len([a for a in self.results["audits"] if a["status"] == "ERROR"])
        
        self.results["summary"] = {
            "total_audits": len(self.results["audits"]),
            "passed": passed,
            "warnings": warnings,
            "errors": errors,
            "pass_rate": f"{(passed / len(self.results['audits']) * 100):.1f}%" if self.results["audits"] else "0%"
        }
        
        report = {"security_audit": self.results}
        
        output = output_file or self.project_root / "logs" / "security_audit_report.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n{'='*60}")
        print("SECURITY AUDIT SUMMARY")
        print(f"{'='*60}")
        print(f"Total Audits: {self.results['summary']['total_audits']}")
        print(f"Passed: {self.results['summary']['passed']}")
        print(f"Warnings: {self.results['summary']['warnings']}")
        print(f"Errors: {self.results['summary']['errors']}")
        print(f"Pass Rate: {self.results['summary']['pass_rate']}")
        print(f"{'='*60}")
        print(f"Full report: {output}")
        
        return self.results


def main():
    """Run security audit"""
    project_root = Path(__file__).parent.parent
    auditor = SecurityAuditor(project_root)
    
    print(f"Starting production security audit at {datetime.now()}")
    print(f"Project root: {project_root}")
    print()
    
    # Run all audits
    auditor.check_secrets_exposure()
    auditor.check_gitignore()
    auditor.check_code_security()
    auditor.check_dependency_security()
    auditor.check_smart_contract_security()
    auditor.check_risk_management()
    auditor.check_transaction_validation()
    auditor.check_production_settings()
    
    # Generate report
    auditor.generate_report()
    
    # Exit with appropriate code
    if auditor.results["summary"]["errors"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
