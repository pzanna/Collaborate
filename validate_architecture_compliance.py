#!/usr/bin/env python3
"""
Architecture Compliance and Integration Test Summary
Final validation that the system is properly architected for MCP
"""

import asyncio
import json
import logging
import sys
import time
from typing import Dict, List, Any
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ArchitectureValidator:
    """Validates system architecture compliance"""
    
    def __init__(self):
        self.validation_results = {}
    
    def validate_docker_compose_architecture(self) -> Dict[str, Any]:
        """Validate docker-compose.yml architecture compliance"""
        logger.info("🔍 Validating docker-compose.yml architecture...")
        
        results = {
            "test_name": "docker_compose_architecture",
            "success": True,
            "violations": [],
            "compliant_services": []
        }
        
        try:
            with open("docker-compose.yml", "r") as f:
                compose_content = f.read()
            
            # Check for agent port mappings (should be none)
            agent_ports = []
            for port in range(8002, 8012):  # Agent port range
                if f":{port}" in compose_content:
                    agent_ports.append(port)
            
            if agent_ports:
                results["success"] = False
                results["violations"].append(f"Found agent port mappings: {agent_ports}")
            else:
                results["compliant_services"].append("No agent port mappings found")
            
            # Check for expected ports only
            expected_ports = ["8001", "9000", "6380", "5433", "80"]  # API Gateway, MCP Server, Redis, Postgres, Nginx
            found_ports = []
            
            for port in expected_ports:
                if f":{port}" in compose_content:
                    found_ports.append(port)
            
            results["found_expected_ports"] = found_ports
            
            # Check for MCP_SERVER_URL environment variables
            mcp_url_count = compose_content.count("MCP_SERVER_URL")
            if mcp_url_count >= 9:  # Should have MCP_SERVER_URL for all 9 agents
                results["compliant_services"].append("All agents have MCP_SERVER_URL configured")
            else:
                results["violations"].append(f"Only {mcp_url_count} agents have MCP_SERVER_URL configured")
            
            # Check for removed HTTP health checks on agents
            if "curl -f http://localhost:800" in compose_content:
                # Look for agent health checks (ports 8002-8011)
                for port in range(8002, 8012):
                    if f"curl -f http://localhost:{port}" in compose_content:
                        results["violations"].append(f"Found HTTP health check for agent port {port}")
            
            logger.info(f"Docker compose validation: {'✅ PASSED' if results['success'] else '❌ FAILED'}")
            
        except Exception as e:
            results["success"] = False
            results["violations"].append(f"Failed to read docker-compose.yml: {e}")
        
        return results
    
    def validate_agent_implementations(self) -> Dict[str, Any]:
        """Validate agent implementations are MCP-compliant"""
        logger.info("🤖 Validating agent implementations...")
        
        results = {
            "test_name": "agent_implementations",
            "success": True,
            "mcp_agents": [],
            "non_mcp_agents": []
        }
        
        # Check for base MCP agent
        try:
            with open("agents/base_mcp_agent.py", "r") as f:
                base_content = f.read()
            
            if "BaseMCPAgent" in base_content and "websockets" in base_content:
                results["mcp_agents"].append("base_mcp_agent.py (foundation)")
            else:
                results["non_mcp_agents"].append("base_mcp_agent.py (invalid implementation)")
                results["success"] = False
                
        except FileNotFoundError:
            results["non_mcp_agents"].append("base_mcp_agent.py (missing)")
            results["success"] = False
        
        # Check for agent implementations
        agent_files = [
            "agents/synthesis/src/synthesis_agent.py",
            "agents/writer/src/writer_agent.py", 
            "agents/database/src/database_agent.py"
        ]
        
        for agent_file in agent_files:
            try:
                with open(agent_file, "r") as f:
                    content = f.read()
                
                if "BaseMCPAgent" in content and "websockets" in content:
                    results["mcp_agents"].append(agent_file)
                elif "FastAPI" in content or "uvicorn" in content:
                    results["non_mcp_agents"].append(f"{agent_file} (still uses FastAPI)")
                    results["success"] = False
                else:
                    results["non_mcp_agents"].append(f"{agent_file} (unknown implementation)")
                    
            except FileNotFoundError:
                results["non_mcp_agents"].append(f"{agent_file} (missing)")
        
        logger.info(f"Agent implementation validation: {'✅ PASSED' if results['success'] else '❌ FAILED'}")
        return results
    
    def validate_mcp_server_connectivity(self) -> Dict[str, Any]:
        """Validate MCP server is running and responsive"""
        logger.info("🔌 Validating MCP server connectivity...")
        
        results = {
            "test_name": "mcp_server_connectivity",
            "success": False,
            "server_status": "unknown",
            "connection_test": "not_attempted"
        }
        
        try:
            # Check if MCP server container is running
            result = subprocess.run(
                ["docker", "compose", "ps", "mcp-server"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and "Up" in result.stdout:
                results["server_status"] = "running"
                
                # Test basic connectivity with our integration test
                test_result = subprocess.run(
                    ["python3", "test_current_mcp_integration.py", "--output", "/tmp/mcp_test.json"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if test_result.returncode == 0:
                    results["success"] = True
                    results["connection_test"] = "passed"
                else:
                    results["connection_test"] = f"failed: {test_result.stderr}"
                    
            else:
                results["server_status"] = "not_running"
                
        except subprocess.TimeoutExpired:
            results["connection_test"] = "timeout"
        except Exception as e:
            results["connection_test"] = f"error: {e}"
        
        logger.info(f"MCP server connectivity: {'✅ PASSED' if results['success'] else '❌ FAILED'}")
        return results
    
    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run comprehensive architecture validation"""
        logger.info("🏗️ Starting Comprehensive Architecture Validation")
        
        # Run all validations
        docker_compose_result = self.validate_docker_compose_architecture()
        agent_impl_result = self.validate_agent_implementations()
        mcp_server_result = self.validate_mcp_server_connectivity()
        
        # Compile results
        all_results = [docker_compose_result, agent_impl_result, mcp_server_result]
        successful_tests = len([r for r in all_results if r["success"]])
        total_tests = len(all_results)
        
        overall_success = successful_tests == total_tests
        
        return {
            "overall_success": overall_success,
            "summary": {
                "total_validations": total_tests,
                "successful_validations": successful_tests,
                "failed_validations": total_tests - successful_tests,
                "success_rate": (successful_tests / total_tests * 100) if total_tests > 0 else 0
            },
            "detailed_results": {
                "docker_compose_architecture": docker_compose_result,
                "agent_implementations": agent_impl_result,
                "mcp_server_connectivity": mcp_server_result
            },
            "architecture_status": "COMPLIANT" if overall_success else "VIOLATIONS_FOUND",
            "recommendations": self.generate_recommendations(all_results)
        }
    
    def generate_recommendations(self, results: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        for result in results:
            if not result["success"]:
                if result["test_name"] == "docker_compose_architecture":
                    recommendations.append("Fix docker-compose.yml: Remove agent port mappings and HTTP health checks")
                elif result["test_name"] == "agent_implementations":
                    recommendations.append("Complete agent conversion: Ensure all agents inherit from BaseMCPAgent")
                elif result["test_name"] == "mcp_server_connectivity":
                    recommendations.append("Start MCP server: Run 'docker compose up mcp-server -d'")
        
        if not recommendations:
            recommendations.append("Architecture is fully compliant - ready for production deployment!")
        
        return recommendations

async def main():
    """Main CLI interface"""
    logger.info("🚀 Architecture Compliance and Integration Test Suite")
    
    validator = ArchitectureValidator()
    results = await validator.run_comprehensive_validation()
    
    # Save results
    with open("architecture_validation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "="*70)
    print("ARCHITECTURE COMPLIANCE & INTEGRATION TEST RESULTS")
    print("="*70)
    
    status_color = "🟢" if results["overall_success"] else "🔴"
    print(f"Overall Status: {status_color} {results['architecture_status']}")
    print(f"Success Rate: {results['summary']['success_rate']:.1f}%")
    print(f"Validations: {results['summary']['successful_validations']}/{results['summary']['total_validations']} passed")
    
    print("\n📋 DETAILED RESULTS:")
    for test_name, test_result in results["detailed_results"].items():
        status = "✅ PASSED" if test_result["success"] else "❌ FAILED"
        print(f"  {test_name.replace('_', ' ').title()}: {status}")
        
        if not test_result["success"] and "violations" in test_result:
            for violation in test_result["violations"]:
                print(f"    - {violation}")
    
    print("\n💡 RECOMMENDATIONS:")
    for rec in results["recommendations"]:
        print(f"  • {rec}")
    
    print(f"\n📁 Detailed results saved to: architecture_validation_results.json")
    
    if results["overall_success"]:
        print("\n🎉 ARCHITECTURE VALIDATION COMPLETE!")
        print("✅ System is ready for MCP-based agent integration testing")
        print("🚀 Proceed with full system deployment for production testing")
    else:
        print("\n⚠️  ARCHITECTURE ISSUES FOUND")
        print("❌ Please address the violations before proceeding")
        print("🔧 Run the recommended fixes and re-validate")
    
    return 0 if results["overall_success"] else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
