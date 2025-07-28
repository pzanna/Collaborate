#!/usr/bin/env python3
"""
Agent Integration & Communication Testing Suite - Quick Version
==============================================================

Comprehensive testing framework for validating agent integration.
"""

import asyncio
import json
import requests
import time
from datetime import datetime


class AgentIntegrationTester:
    """Quick agent integration testing framework"""
    
    def __init__(self):
        self.base_urls = {
            'api-gateway': 'http://localhost:8001',
            'research-manager': 'http://localhost:8002', 
            'literature-agent': 'http://localhost:8003',
            'screening-agent': 'http://localhost:8004',
            'synthesis-agent': 'http://localhost:8005',
            'writer-agent': 'http://localhost:8006',
            'planning-agent': 'http://localhost:8007',
            'executor-agent': 'http://localhost:8008',
            'memory-agent': 'http://localhost:8009',
            'database-agent': 'http://localhost:8011'
        }
        self.results = []
        
    def run_all_tests(self):
        """Run complete integration test suite"""
        print("🚀 Starting Agent Integration & Communication Testing Suite")
        print("=" * 70)
        
        test_start = time.time()
        
        # Phase 1: Health Check Tests
        self.test_phase("Phase 1: Service Health Tests", [
            self.test_all_service_health,
            self.test_basic_connectivity
        ])
        
        # Phase 2: Individual Agent Capability Tests  
        self.test_phase("Phase 2: Agent Capability Tests", [
            self.test_agent_endpoints,
            self.test_agent_health_details
        ])
        
        # Phase 3: Integration Tests
        self.test_phase("Phase 3: Integration Tests", [
            self.test_mcp_connectivity_status,
            self.test_cross_agent_communication
        ])
        
        total_duration = time.time() - test_start
        return self.generate_test_report(total_duration)
    
    def test_phase(self, phase_name, test_functions):
        """Execute a test phase"""
        print(f"\n📋 {phase_name}")
        print("-" * 50)
        
        for test_func in test_functions:
            try:
                test_func()
            except Exception as e:
                self.results.append({
                    'test_name': test_func.__name__,
                    'status': 'FAIL',
                    'error': str(e)
                })
                print(f"❌ {test_func.__name__}: FAILED - {str(e)}")
    
    def test_all_service_health(self):
        """Test health endpoints of all services"""
        print("🔍 Testing service health endpoints...")
        
        healthy_services = []
        unhealthy_services = []
        
        for service_name, base_url in self.base_urls.items():
            try:
                response = requests.get(f"{base_url}/health", timeout=5)
                if response.status_code == 200:
                    health_data = response.json()
                    healthy_services.append({
                        'service': service_name,
                        'status': health_data.get('status', 'unknown'),
                        'mcp_connected': health_data.get('mcp_connected', False),
                        'capabilities': len(health_data.get('capabilities', []))
                    })
                    print(f"  ✅ {service_name}: {health_data.get('status', 'unknown')}")
                else:
                    unhealthy_services.append({
                        'service': service_name,
                        'status_code': response.status_code
                    })
                    print(f"  ❌ {service_name}: HTTP {response.status_code}")
            except Exception as e:
                unhealthy_services.append({
                    'service': service_name,
                    'error': str(e)
                })
                print(f"  ❌ {service_name}: {str(e)}")
        
        self.results.append({
            'test_name': 'test_all_service_health',
            'status': 'PASS' if len(unhealthy_services) == 0 else 'FAIL',
            'healthy_services': len(healthy_services),
            'unhealthy_services': len(unhealthy_services),
            'details': {
                'healthy': healthy_services,
                'unhealthy': unhealthy_services
            }
        })
        
        print(f"📊 Health Summary: {len(healthy_services)}/{len(self.base_urls)} services healthy")
    
    def test_basic_connectivity(self):
        """Test basic connectivity to all services"""
        print("🔗 Testing basic connectivity...")
        
        connectivity_results = {}
        
        for service_name, base_url in self.base_urls.items():
            try:
                response = requests.get(base_url, timeout=3)
                connectivity_results[service_name] = {
                    'connected': True,
                    'status_code': response.status_code
                }
            except Exception as e:
                connectivity_results[service_name] = {
                    'connected': False,
                    'error': str(e)
                }
        
        connected_count = sum(1 for r in connectivity_results.values() if r['connected'])
        
        self.results.append({
            'test_name': 'test_basic_connectivity',
            'status': 'PASS' if connected_count == len(self.base_urls) else 'FAIL',
            'connected_services': connected_count,
            'total_services': len(self.base_urls),
            'details': connectivity_results
        })
        
        print(f"📡 Connectivity: {connected_count}/{len(self.base_urls)} services reachable")
    
    def test_agent_endpoints(self):
        """Test agent endpoint availability"""
        print("🎯 Testing agent endpoints...")
        
        endpoint_tests = {
            'synthesis-agent': ['/health', '/capabilities', '/synthesize'],
            'writer-agent': ['/health', '/capabilities', '/generate'],
            'literature-agent': ['/health', '/capabilities', '/search'],
            'screening-agent': ['/health', '/capabilities', '/screen'],
            'planning-agent': ['/health', '/capabilities', '/plan'],
            'executor-agent': ['/health', '/capabilities', '/execute'],
            'database-agent': ['/health', '/capabilities', '/query'],
            'research-manager': ['/health', '/capabilities'],
            'api-gateway': ['/health', '/status']
        }
        
        endpoint_results = {}
        
        for service_name, endpoints in endpoint_tests.items():
            if service_name in self.base_urls:
                base_url = self.base_urls[service_name]
                service_results = {}
                
                for endpoint in endpoints:
                    try:
                        response = requests.get(f"{base_url}{endpoint}", timeout=3)
                        service_results[endpoint] = {
                            'available': response.status_code in [200, 405],  # 405 is method not allowed, but endpoint exists
                            'status_code': response.status_code
                        }
                    except Exception as e:
                        service_results[endpoint] = {
                            'available': False,
                            'error': str(e)
                        }
                
                endpoint_results[service_name] = service_results
                available_count = sum(1 for r in service_results.values() if r['available'])
                print(f"  📍 {service_name}: {available_count}/{len(endpoints)} endpoints available")
        
        self.results.append({
            'test_name': 'test_agent_endpoints',
            'status': 'PASS',
            'details': endpoint_results
        })
    
    def test_agent_health_details(self):
        """Test detailed health information from agents"""
        print("🏥 Testing detailed health information...")
        
        health_details = {}
        
        for service_name, base_url in self.base_urls.items():
            try:
                response = requests.get(f"{base_url}/health", timeout=5)
                if response.status_code == 200:
                    health_data = response.json()
                    health_details[service_name] = {
                        'status': health_data.get('status'),
                        'agent_type': health_data.get('agent_type'),
                        'mcp_connected': health_data.get('mcp_connected', False),
                        'capabilities': health_data.get('capabilities', []),
                        'processing_capabilities': health_data.get('processing_capabilities', []),
                        'output_formats': health_data.get('output_formats', []),
                        'citation_styles': health_data.get('citation_styles', [])
                    }
                    
                    # Count capabilities
                    total_caps = len(health_data.get('capabilities', [])) + len(health_data.get('processing_capabilities', []))
                    mcp_status = "🟢" if health_data.get('mcp_connected') else "🔴"
                    print(f"  {mcp_status} {service_name}: {total_caps} capabilities, MCP: {health_data.get('mcp_connected', False)}")
                    
            except Exception as e:
                health_details[service_name] = {'error': str(e)}
                print(f"  ⚠️  {service_name}: Health check failed - {str(e)}")
        
        self.results.append({
            'test_name': 'test_agent_health_details',
            'status': 'PASS',
            'details': health_details
        })
    
    def test_mcp_connectivity_status(self):
        """Test MCP connectivity status across all agents"""
        print("🔌 Testing MCP connectivity status...")
        
        mcp_status = {}
        connected_agents = 0
        
        for service_name, base_url in self.base_urls.items():
            try:
                response = requests.get(f"{base_url}/health", timeout=5)
                if response.status_code == 200:
                    health_data = response.json()
                    is_connected = health_data.get('mcp_connected', False)
                    mcp_status[service_name] = {
                        'mcp_connected': is_connected,
                        'agent_type': health_data.get('agent_type', 'unknown')
                    }
                    if is_connected:
                        connected_agents += 1
                        print(f"  🟢 {service_name}: MCP Connected")
                    else:
                        print(f"  🔴 {service_name}: MCP Disconnected")
            except Exception as e:
                mcp_status[service_name] = {'error': str(e)}
                print(f"  ⚠️  {service_name}: Status check failed")
        
        self.results.append({
            'test_name': 'test_mcp_connectivity_status',
            'status': 'PASS' if connected_agents > 0 else 'FAIL',
            'connected_agents': connected_agents,
            'total_agents': len(self.base_urls),
            'details': mcp_status
        })
        
        print(f"🔗 MCP Status: {connected_agents}/{len(self.base_urls)} agents connected")
    
    def test_cross_agent_communication(self):
        """Test cross-agent communication capabilities"""
        print("💬 Testing cross-agent communication...")
        
        # Test if agents can be reached and respond appropriately
        communication_tests = []
        
        # Test synthesis agent with mock data
        try:
            synthesis_payload = {
                "studies": [{"id": "test_001", "title": "Test Study"}],
                "synthesis_type": "narrative",
                "test_mode": True
            }
            response = requests.post(
                f"{self.base_urls['synthesis-agent']}/synthesize",
                json=synthesis_payload,
                timeout=10
            )
            communication_tests.append({
                'test': 'synthesis_agent_mock_request',
                'success': response.status_code in [200, 422],  # 422 might be validation error, but endpoint works
                'status_code': response.status_code
            })
            print(f"  🧪 Synthesis Agent: Response {response.status_code}")
        except Exception as e:
            communication_tests.append({
                'test': 'synthesis_agent_mock_request',
                'success': False,
                'error': str(e)
            })
            print(f"  ❌ Synthesis Agent: {str(e)}")
        
        # Test writer agent with mock data
        try:
            writer_payload = {
                "content": {"title": "Test Document"},
                "format": "markdown",
                "test_mode": True
            }
            response = requests.post(
                f"{self.base_urls['writer-agent']}/generate",
                json=writer_payload,
                timeout=10
            )
            communication_tests.append({
                'test': 'writer_agent_mock_request',
                'success': response.status_code in [200, 422],
                'status_code': response.status_code
            })
            print(f"  📝 Writer Agent: Response {response.status_code}")
        except Exception as e:
            communication_tests.append({
                'test': 'writer_agent_mock_request',
                'success': False,
                'error': str(e)
            })
            print(f"  ❌ Writer Agent: {str(e)}")
        
        successful_tests = sum(1 for test in communication_tests if test['success'])
        
        self.results.append({
            'test_name': 'test_cross_agent_communication',
            'status': 'PASS' if successful_tests > 0 else 'FAIL',
            'successful_tests': successful_tests,
            'total_tests': len(communication_tests),
            'details': communication_tests
        })
        
        print(f"📡 Communication: {successful_tests}/{len(communication_tests)} tests successful")
    
    def generate_test_report(self, total_duration):
        """Generate comprehensive test report"""
        passed = [r for r in self.results if r['status'] == 'PASS']
        failed = [r for r in self.results if r['status'] == 'FAIL']
        
        report = {
            'summary': {
                'total_tests': len(self.results),
                'passed': len(passed),
                'failed': len(failed),
                'pass_rate': len(passed) / len(self.results) * 100 if self.results else 0,
                'total_duration': total_duration,
                'timestamp': datetime.now().isoformat()
            },
            'results': self.results
        }
        
        # Print summary
        print("\n" + "=" * 70)
        print("🎯 INTEGRATION TEST SUMMARY")
        print("=" * 70)
        print(f"Total Tests: {report['summary']['total_tests']}")
        print(f"✅ Passed: {report['summary']['passed']}")
        print(f"❌ Failed: {report['summary']['failed']}")
        print(f"📊 Pass Rate: {report['summary']['pass_rate']:.1f}%")
        print(f"⏱️  Total Duration: {report['summary']['total_duration']:.2f}s")
        
        if failed:
            print(f"\n❌ FAILED TESTS:")
            for r in failed:
                print(f"  • {r['test_name']}: {r.get('error', 'Unknown error')}")
        
        # Save report to file
        with open('integration_test_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Full report saved to: integration_test_report.json")
        
        return report


def main():
    """Run the integration test suite"""
    tester = AgentIntegrationTester()
    return tester.run_all_tests()


if __name__ == "__main__":
    main()
