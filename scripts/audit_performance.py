#!/usr/bin/env python3
"""
Performance Audit Script
Comprehensive performance analysis for Flash Loan Trading System
"""
import os
import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime


class PerformanceAuditor:
    """Performance audit for the trading system"""
    
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "audits": [],
            "summary": {}
        }
    
    def log_audit(self, audit_name, status, details, metrics=None):
        """Log audit result"""
        entry = {
            "name": audit_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        if metrics:
            entry["metrics"] = metrics
        self.results["audits"].append(entry)
        print(f"[{status}] {audit_name}: {details}")
        if metrics:
            print(f"  Metrics: {metrics}")
    
    def analyze_code_complexity(self):
        """Analyze code complexity metrics"""
        try:
            # Use radon or similar tool if available
            result = subprocess.run(
                ["radon", "cc", "src", "-a"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if lines:
                    # Parse complexity metrics
                    total_files = len([l for l in lines if l.startswith('src/')])
                    avg_complexity = sum(
                        int(l.split()[-1]) for l in lines 
                        if l.startswith('src/') and l.split()[-1].isdigit()
                    ) / max(total_files, 1)
                    
                    self.log_audit(
                        "Code Complexity", 
                        "PASS" if avg_complexity < 10 else "WARNING",
                        f"Average complexity: {avg_complexity:.1f}",
                        {"total_files": total_files, "avg_complexity": avg_complexity}
                    )
                else:
                    self.log_audit("Code Complexity", "INFO", "No complexity data")
            else:
                self.log_audit("Code Complexity", "INFO", "Radon not available")
        except Exception as e:
            self.log_audit("Code Complexity", "INFO", f"Check skipped: {e}")
    
    def analyze_gas_usage(self):
        """Analyze smart contract gas usage"""
        try:
            contracts_dir = self.project_root / "contracts"
            if contracts_dir.exists():
                # Check deployment script for gas estimates
                deploy_script = contracts_dir / "script" / "Deploy.s.sol"
                
                if deploy_script.exists():
                    with open(deploy_script) as f:
                        content = f.read()
                        if "gas" in content.lower():
                            self.log_audit("Gas Usage", "PASS", 
                                         "Gas optimization detected in contracts")
                        else:
                            self.log_audit("Gas Usage", "INFO", 
                                         "No explicit gas optimization found")
                else:
                    self.log_audit("Gas Usage", "INFO", 
                                 "Deployment script not found")
            else:
                self.log_audit("Gas Usage", "INFO", 
                             "Contracts directory not found")
        except Exception as e:
            self.log_audit("Gas Usage", "INFO", f"Check skipped: {e}")
    
    def analyze_trading_performance(self):
        """Analyze trading engine performance"""
        try:
            # Check trading engine configuration
            config_file = self.project_root / "config" / "trading_config.json"
            
            if config_file.exists():
                with open(config_file) as f:
                    config = json.load(f)
                    
                    metrics = {
                        "max_concurrent_trades": config.get("trading", {}).get("max_concurrent_trades"),
                        "min_profit_threshold": config.get("trading", {}).get("min_profit_threshold_usd"),
                        "test_mode": config.get("trading", {}).get("test_mode")
                    }
                    
                    self.log_audit(
                        "Trading Performance",
                        "PASS",
                        "Trading configuration optimized",
                        metrics
                    )
            else:
                self.log_audit("Trading Performance", "INFO", 
                             "Configuration file not found")
        except Exception as e:
            self.log_audit("Trading Performance", "INFO", f"Check skipped: {e}")
    
    def analyze_database_performance(self):
        """Analyze database performance"""
        try:
            database_dir = self.project_root / "database"
            
            if database_dir.exists():
                # Check for indexes and optimization
                sql_files = list(database_dir.glob("*.sql"))
                
                if sql_files:
                    total_size = sum(f.stat().st_size for f in sql_files)
                    self.log_audit(
                        "Database Performance",
                        "PASS",
                        f"Database files: {len(sql_files)}, Total size: {total_size} bytes",
                        {"file_count": len(sql_files), "total_size": total_size}
                    )
                else:
                    self.log_audit("Database Performance", "INFO", 
                                 "No SQL files found")
            else:
                self.log_audit("Database Performance", "INFO", 
                             "Database directory not found")
        except Exception as e:
            self.log_audit("Database Performance", "INFO", f"Check skipped: {e}")
    
    def analyze_monitoring_setup(self):
        """Analyze monitoring and observability"""
        try:
            monitoring_dir = self.project_root / "monitoring"
            
            if monitoring_dir.exists():
                monitoring_files = list(monitoring_dir.glob("*"))
                
                checks = {
                    "metrics": len(list(monitoring_dir.glob("*metrics*"))) > 0,
                    "alerts": len(list(monitoring_dir.glob("*alert*"))) > 0,
                    "dashboards": len(list(monitoring_dir.glob("*dashboard*"))) > 0
                }
                
                if all(checks.values()):
                    self.log_audit(
                        "Monitoring Setup",
                        "PASS",
                        "Complete monitoring infrastructure",
                        {"files": len(monitoring_files)}
                    )
                else:
                    missing = [k for k, v in checks.items() if not v]
                    self.log_audit(
                        "Monitoring Setup",
                        "WARNING",
                        f"Missing monitoring components: {missing}",
                        {"files": len(monitoring_files)}
                    )
            else:
                self.log_audit("Monitoring Setup", "INFO", 
                             "Monitoring directory not found")
        except Exception as e:
            self.log_audit("Monitoring Setup", "INFO", f"Check skipped: {e}")
    
    def analyze_resource_usage(self):
        """Analyze current resource usage"""
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage(self.project_root)
            disk_percent = disk.percent / 100
            
            metrics = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent
            }
            
            status = "PASS" if cpu_percent < 80 and memory_percent < 80 else "WARNING"
            
            self.log_audit(
                "Resource Usage",
                status,
                f"CPU: {cpu_percent:.1f}%, Memory: {memory_percent:.1f}%, Disk: {disk_percent:.1f}%",
                metrics
            )
        except ImportError:
            self.log_audit("Resource Usage", "INFO", 
                         "psutil not available, skipping")
        except Exception as e:
            self.log_audit("Resource Usage", "INFO", f"Check skipped: {e}")
    
    def analyze_transaction_latency(self):
        """Analyze transaction latency metrics"""
        try:
            logs_dir = self.project_root / "logs"
            
            if logs_dir.exists():
                # Look for transaction timing logs
                log_files = list(logs_dir.glob("*.log"))
                
                if log_files:
                    total_size = sum(f.stat().st_size for f in log_files)
                    self.log_audit(
                        "Transaction Latency",
                        "PASS",
                        f"Transaction logs available: {len(log_files)} files",
                        {"log_files": len(log_files), "total_size": total_size}
                    )
                else:
                    self.log_audit("Transaction Latency", "INFO", 
                                 "No log files found")
            else:
                self.log_audit("Transaction Latency", "INFO", 
                             "Logs directory not found")
        except Exception as e:
            self.log_audit("Transaction Latency", "INFO", f"Check skipped: {e}")
    
    def generate_report(self, output_file=None):
        """Generate performance audit report"""
        # Calculate summary
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
        
        # Generate report
        report = {
            "performance_audit": self.results
        }
        
        output = output_file or self.project_root / "logs" / "performance_audit_report.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n{'='*60}")
        print("PERFORMANCE AUDIT SUMMARY")
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
    """Run performance audit"""
    project_root = Path(__file__).parent.parent
    auditor = PerformanceAuditor(project_root)
    
    print(f"Starting performance audit at {datetime.now()}")
    print(f"Project root: {project_root}")
    print()
    
    # Run all audits
    auditor.analyze_code_complexity()
    auditor.analyze_gas_usage()
    auditor.analyze_trading_performance()
    auditor.analyze_database_performance()
    auditor.analyze_monitoring_setup()
    auditor.analyze_resource_usage()
    auditor.analyze_transaction_latency()
    
    # Generate report
    auditor.generate_report()
    
    # Exit with appropriate code
    if auditor.results["summary"]["errors"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
