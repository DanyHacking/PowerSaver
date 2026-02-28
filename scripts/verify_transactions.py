#!/usr/bin/env python3
"""
Transaction Verification Script
Verify and analyze blockchain transactions on local network
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from web3 import Web3
from web3.middleware import geth_poa_middleware


class TransactionVerifier:
    """Verify blockchain transactions"""
    
    def __init__(self, rpc_url, project_root):
        self.rpc_url = rpc_url
        self.project_root = Path(project_root)
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "verifications": [],
            "summary": {}
        }
    
    def log_verification(self, name, status, details):
        """Log verification result"""
        self.results["verifications"].append({
            "name": name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        print(f"[{status}] {name}: {details}")
    
    def verify_node_connectivity(self):
        """Verify connection to blockchain node"""
        try:
            block_number = self.w3.eth.block_number
            self.log_verification(
                "Node Connectivity",
                "PASS",
                f"Connected to block {block_number}"
            )
            return True
        except Exception as e:
            self.log_verification(
                "Node Connectivity",
                "ERROR",
                f"Failed to connect: {str(e)}"
            )
            return False
    
    def verify_contract_deployment(self):
        """Verify smart contract deployment"""
        try:
            # Get deployment addresses
            deployment_file = self.project_root / "artifacts" / "deployment_addresses.json"
            
            if deployment_file.exists():
                with open(deployment_file) as f:
                    addresses = json.load(f)
                    
                    for contract_name, address in addresses.items():
                        # Check if contract exists at address
                        code = self.w3.eth.get_code(address)
                        
                        if code and len(code) > 2:
                            self.log_verification(
                                f"Contract: {contract_name}",
                                "PASS",
                                f"Deployed at {address}"
                            )
                        else:
                            self.log_verification(
                                f"Contract: {contract_name}",
                                "WARNING",
                                f"No code at {address}"
                            )
            else:
                self.log_verification(
                    "Contract Deployment",
                    "INFO",
                    "Deployment file not found"
                )
        except Exception as e:
            self.log_verification(
                "Contract Deployment",
                "ERROR",
                f"Verification failed: {str(e)}"
            )
    
    def verify_transaction_history(self):
        """Verify transaction history"""
        try:
            # Get recent transactions
            latest_block = self.w3.eth.block_number
            
            if latest_block > 0:
                recent_block = self.w3.eth.get_block(latest_block - 1)
                tx_count = len(recent_block.get('transactions', []))
                
                self.log_verification(
                    "Transaction History",
                    "PASS",
                    f"Latest block: {latest_block}, Transactions: {tx_count}"
                )
            else:
                self.log_verification(
                    "Transaction History",
                    "INFO",
                    "No transactions yet"
                )
        except Exception as e:
            self.log_verification(
                "Transaction History",
                "ERROR",
                f"Failed to verify: {str(e)}"
            )
    
    def verify_gas_prices(self):
        """Verify gas price metrics"""
        try:
            gas_price = self.w3.eth.gas_price
            gas_price_gwei = gas_price / 10**9
            
            self.log_verification(
                "Gas Prices",
                "PASS",
                f"Current gas price: {gas_price_gwei:.2f} Gwei"
            )
        except Exception as e:
            self.log_verification(
                "Gas Prices",
                "ERROR",
                f"Failed to get gas price: {str(e)}"
            )
    
    def verify_account_balances(self):
        """Verify account balances"""
        try:
            # Get test accounts
            accounts = self.w3.eth.accounts[:5]
            
            balances = []
            for account in accounts:
                balance = self.w3.eth.get_balance(account)
                balance_eth = balance / 10**18
                balances.append(balance_eth)
                
                self.log_verification(
                    f"Account: {account[:10]}...",
                    "PASS",
                    f"Balance: {balance_eth:.4f} ETH"
                )
            
            total_balance = sum(balances)
            self.log_verification(
                "Total Balances",
                "INFO",
                f"Total: {total_balance:.4f} ETH across {len(accounts)} accounts"
            )
        except Exception as e:
            self.log_verification(
                "Account Balances",
                "ERROR",
                f"Failed to verify: {str(e)}"
            )
    
    def verify_network_status(self):
        """Verify network status"""
        try:
            chain_id = self.w3.eth.chain_id
            syncing = self.w3.eth.syncing
            
            status = "Syncing" if syncing else "Synced"
            sync_progress = syncing.get('current', 0) if syncing else 0
            
            self.log_verification(
                "Network Status",
                "PASS",
                f"Chain ID: {chain_id}, Status: {status}, Block: {sync_progress}"
            )
        except Exception as e:
            self.log_verification(
                "Network Status",
                "ERROR",
                f"Failed to verify: {str(e)}"
            )
    
    def verify_flash_loan_pool(self):
        """Verify flash loan pool status"""
        try:
            # Check Aave pool if configured
            aave_pool_addr = os.getenv("AAVE_V3_POOL_ADDRESS")
            
            if aave_pool_addr:
                code = self.w3.eth.get_code(aave_pool_addr)
                
                if code and len(code) > 2:
                    self.log_verification(
                        "Flash Loan Pool",
                        "PASS",
                        f"Aave pool active at {aave_pool_addr}"
                    )
                else:
                    self.log_verification(
                        "Flash Loan Pool",
                        "WARNING",
                        f"Aave pool not found at {aave_pool_addr}"
                    )
            else:
                self.log_verification(
                    "Flash Loan Pool",
                    "INFO",
                    "Pool address not configured"
                )
        except Exception as e:
            self.log_verification(
                "Flash Loan Pool",
                "ERROR",
                f"Failed to verify: {str(e)}"
            )
    
    def generate_report(self, output_file=None):
        """Generate verification report"""
        passed = len([v for v in self.results["verifications"] if v["status"] == "PASS"])
        warnings = len([v for v in self.results["verifications"] if v["status"] == "WARNING"])
        errors = len([v for v in self.results["verifications"] if v["status"] == "ERROR"])
        
        self.results["summary"] = {
            "total_verifications": len(self.results["verifications"]),
            "passed": passed,
            "warnings": warnings,
            "errors": errors,
            "pass_rate": f"{(passed / len(self.results['verifications']) * 100):.1f}%" if self.results["verifications"] else "0%"
        }
        
        report = {"transaction_verification": self.results}
        
        output = output_file or self.project_root / "logs" / "transaction_verification_report.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n{'='*60}")
        print("TRANSACTION VERIFICATION SUMMARY")
        print(f"{'='*60}")
        print(f"Total Verifications: {self.results['summary']['total_verifications']}")
        print(f"Passed: {self.results['summary']['passed']}")
        print(f"Warnings: {self.results['summary']['warnings']}")
        print(f"Errors: {self.results['summary']['errors']}")
        print(f"Pass Rate: {self.results['summary']['pass_rate']}")
        print(f"{'='*60}")
        print(f"Full report: {output}")
        
        return self.results


def main():
    """Run transaction verification"""
    project_root = Path(__file__).parent.parent
    rpc_url = os.getenv("LOCAL_RPC_URL", "http://localhost:8545")
    
    verifier = TransactionVerifier(rpc_url, project_root)
    
    print(f"Starting transaction verification at {datetime.now()}")
    print(f"RPC URL: {rpc_url}")
    print()
    
    # Run all verifications
    if verifier.verify_node_connectivity():
        verifier.verify_contract_deployment()
        verifier.verify_transaction_history()
        verifier.verify_gas_prices()
        verifier.verify_account_balances()
        verifier.verify_network_status()
        verifier.verify_flash_loan_pool()
    
    # Generate report
    verifier.generate_report()
    
    # Exit with appropriate code
    if verifier.results["summary"]["errors"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
