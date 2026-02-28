"""
Test Coverage Audit Script
Verifies 100% test coverage for User Portal backend modules.
"""

import os
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Set

class TestCoverageAuditor:
    """Audits test coverage for User Portal backend modules."""
    
    def __init__(self, backend_path: str):
        self.backend_path = Path(backend_path)
        self.apps_path = self.backend_path / "apps"
        self.coverage_results = {}
        self.missing_coverage = {}
        self.uncovered_modules = set()
        
    def run_coverage_analysis(self) -> Dict:
        """Run comprehensive coverage analysis."""
        print("🔍 Starting Test Coverage Audit...")
        
        # Step 1: Run coverage report
        coverage_data = self._run_coverage_report()
        
        # Step 2: Analyze module coverage
        self._analyze_module_coverage(coverage_data)
        
        # Step 3: Identify missing test files
        self._identify_missing_tests()
        
        # Step 4: Generate coverage report
        audit_report = self._generate_audit_report()
        
        return audit_report
    
    def _run_coverage_report(self) -> Dict:
        """Run coverage report and parse results."""
        print("📊 Running coverage report...")
        
        try:
            # Run coverage with JSON output
            cmd = [
                "python", "-m", "coverage",
                "run",
                "--source=apps",
                "--omit=*/migrations/*,*/tests/*,*/__pycache__/*",
                "manage.py",
                "test",
                "--settings=config.settings.test_sqlite"
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.backend_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"❌ Coverage run failed: {result.stderr}")
                return {}
            
            # Generate JSON report
            json_cmd = [
                "python", "-m", "coverage",
                "json",
                "--show-contexts"
            ]
            
            json_result = subprocess.run(
                json_cmd,
                cwd=self.backend_path,
                capture_output=True,
                text=True
            )
            
            if json_result.returncode != 0:
                print(f"❌ JSON report failed: {json_result.stderr}")
                return {}
            
            # Parse JSON coverage data
            coverage_file = self.backend_path / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file, 'r') as f:
                    return json.load(f)
            
        except Exception as e:
            print(f"❌ Error running coverage: {e}")
            
        return {}
    
    def _analyze_module_coverage(self, coverage_data: Dict):
        """Analyze coverage data for each module."""
        print("🔍 Analyzing module coverage...")
        
        # Define expected modules and their test files
        expected_modules = {
            'customer_auth': {
                'models': 'apps/customer_auth/models.py',
                'services': 'apps/customer_auth/services.py',
                'views': 'apps/customer_auth/views.py',
                'tests': [
                    'apps/customer_auth/tests/test_models.py',
                    'apps/customer_auth/tests/test_services.py',
                    'apps/customer_auth/tests/test_views.py',
                    'apps/customer_auth/tests/test_auth_flows.py'
                ]
            },
            'user_portal': {
                'models': 'apps/user_portal/models.py',
                'services': 'apps/user_portal/services.py',
                'views': 'apps/user_portal/views.py',
                'tests': [
                    'apps/user_portal/tests/test_models_minimal.py',
                    'apps/user_portal/tests/test_services_minimal.py',
                    'apps/user_portal/tests/test_views.py',
                    'apps/user_portal/tests/test_api_endpoints.py'
                ]
            },
            'user_preferences': {
                'models': 'apps/user_preferences/models.py',
                'services': 'apps/user_preferences/services.py',
                'views': 'apps/user_preferences/views.py',
                'tests': [
                    'apps/user_preferences/tests/test_models_minimal.py',
                    'apps/user_preferences/tests/test_services.py',
                    'apps/user_preferences/tests/test_views.py'
                ]
            }
        }
        
        # Analyze each module
        for app_name, module_info in expected_modules.items():
            app_coverage = self._analyze_app_coverage(
                app_name, module_info, coverage_data
            )
            self.coverage_results[app_name] = app_coverage
    
    def _analyze_app_coverage(self, app_name: str, module_info: Dict, coverage_data: Dict) -> Dict:
        """Analyze coverage for a specific app."""
        app_coverage = {
            'total_statements': 0,
            'covered_statements': 0,
            'coverage_percentage': 0.0,
            'modules': {},
            'missing_tests': [],
            'coverage_gaps': []
        }
        
        # Analyze each module file
        for module_type, module_path in module_info.items():
            if module_type == 'tests':
                continue  # Skip tests, analyze separately
                
            full_path = self.backend_path / module_path
            if not full_path.exists():
                app_coverage['missing_tests'].append(f"{module_path} (file missing)")
                continue
            
            # Get coverage for this file
            file_coverage = self._get_file_coverage(module_path, coverage_data)
            if file_coverage:
                app_coverage['modules'][module_type] = file_coverage
                app_coverage['total_statements'] += file_coverage['statements']
                app_coverage['covered_statements'] += file_coverage['covered']
                
                # Check for coverage gaps
                if file_coverage['coverage'] < 100:
                    app_coverage['coverage_gaps'].append({
                        'module': module_type,
                        'file': module_path,
                        'coverage': file_coverage['coverage'],
                        'missing_lines': file_coverage.get('missing_lines', [])
                    })
        
        # Calculate overall coverage
        if app_coverage['total_statements'] > 0:
            app_coverage['coverage_percentage'] = (
                app_coverage['covered_statements'] / app_coverage['total_statements'] * 100
            )
        
        # Check for missing test files
        existing_tests = []
        for test_file in module_info.get('tests', []):
            test_path = self.backend_path / test_file
            if test_path.exists():
                existing_tests.append(test_file)
            else:
                app_coverage['missing_tests'].append(test_file)
        
        app_coverage['existing_tests'] = existing_tests
        
        return app_coverage
    
    def _get_file_coverage(self, file_path: str, coverage_data: Dict) -> Dict:
        """Get coverage data for a specific file."""
        files = coverage_data.get('files', {})
        
        # Find the file in coverage data
        for file_info in files.values():
            if file_info.get('relative_path') == file_path:
                summary = file_info.get('summary', {})
                return {
                    'statements': summary.get('num_statements', 0),
                    'covered': summary.get('covered_lines', 0),
                    'coverage': summary.get('percent_covered', 0.0),
                    'missing_lines': file_info.get('missing_lines', [])
                }
        
        return {}
    
    def _identify_missing_tests(self):
        """Identify modules that are missing test coverage."""
        print("🔍 Identifying missing test files...")
        
        # Define all expected test files
        expected_test_files = [
            'apps/customer_auth/tests/test_models.py',
            'apps/customer_auth/tests/test_services.py',
            'apps/customer_auth/tests/test_views.py',
            'apps/customer_auth/tests/test_auth_flows.py',
            'apps/user_portal/tests/test_models_minimal.py',
            'apps/user_portal/tests/test_services_minimal.py',
            'apps/user_portal/tests/test_views.py',
            'apps/user_portal/tests/test_api_endpoints.py',
            'apps/user_portal/tests/test_search_nlp.py',
            'apps/user_portal/tests/test_business_logic.py',
            'apps/user_portal/tests/test_performance.py',
            'apps/user_portal/tests/test_security.py',
            'apps/user_portal/tests/test_error_handling.py',
            'apps/user_portal/tests/test_integration_flows.py',
            'apps/user_preferences/tests/test_models_minimal.py',
            'apps/user_preferences/tests/test_services.py',
            'apps/user_preferences/tests/test_views.py'
        ]
        
        # Check which test files exist
        for test_file in expected_test_files:
            test_path = self.backend_path / test_file
            if not test_path.exists():
                self.uncovered_modules.add(test_file)
    
    def _generate_audit_report(self) -> Dict:
        """Generate comprehensive audit report."""
        print("📋 Generating audit report...")
        
        # Calculate overall coverage
        total_statements = sum(
            app['total_statements'] for app in self.coverage_results.values()
        )
        total_covered = sum(
            app['covered_statements'] for app in self.coverage_results.values()
        )
        overall_coverage = (total_covered / total_statements * 100) if total_statements > 0 else 0
        
        # Generate recommendations
        recommendations = self._generate_recommendations()
        
        audit_report = {
            'summary': {
                'overall_coverage_percentage': overall_coverage,
                'total_statements': total_statements,
                'total_covered': total_covered,
                'apps_analyzed': len(self.coverage_results),
                'missing_test_files': len(self.uncovered_modules),
                'coverage_goal_met': overall_coverage >= 100.0
            },
            'app_coverage': self.coverage_results,
            'missing_test_files': list(self.uncovered_modules),
            'recommendations': recommendations,
            'status': 'PASS' if overall_coverage >= 100.0 else 'FAIL'
        }
        
        return audit_report
    
    def _generate_recommendations(self) -> List[Dict]:
        """Generate recommendations based on coverage gaps."""
        recommendations = []
        
        # Check for missing test files
        if self.uncovered_modules:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Missing Tests',
                'description': f'{len(self.uncovered_modules)} test files are missing',
                'action': 'Create missing test files to achieve 100% coverage',
                'files': list(self.uncovered_modules)
            })
        
        # Check for coverage gaps in existing modules
        for app_name, app_data in self.coverage_results.items():
            if app_data['coverage_gaps']:
                recommendations.append({
                    'priority': 'MEDIUM',
                    'category': 'Coverage Gaps',
                    'description': f'{app_name} has {len(app_data["coverage_gaps"])} modules with <100% coverage',
                    'action': 'Add tests to cover missing lines',
                    'gaps': app_data['coverage_gaps']
                })
        
        # Check for low coverage apps
        for app_name, app_data in self.coverage_results.items():
            if app_data['coverage_percentage'] < 95:
                recommendations.append({
                    'priority': 'HIGH',
                    'category': 'Low Coverage',
                    'description': f'{app_name} has only {app_data["coverage_percentage"]:.1f}% coverage',
                    'action': 'Improve test coverage for this app',
                    'app': app_name,
                    'current_coverage': app_data['coverage_percentage']
                })
        
        return recommendations
    
    def print_audit_report(self, report: Dict):
        """Print formatted audit report."""
        print("\n" + "="*80)
        print("📊 TEST COVERAGE AUDIT REPORT")
        print("="*80)
        
        # Summary
        summary = report['summary']
        print(f"\n📈 OVERALL COVERAGE: {summary['overall_coverage_percentage']:.1f}%")
        print(f"📋 STATUS: {summary['status']}")
        print(f"📁 APPS ANALYZED: {summary['apps_analyzed']}")
        print(f"📄 MISSING TEST FILES: {summary['missing_test_files']}")
        print(f"🎯 GOAL MET: {'✅ YES' if summary['coverage_goal_met'] else '❌ NO'}")
        
        # App coverage breakdown
        print(f"\n📱 APP COVERAGE BREAKDOWN:")
        print("-" * 50)
        for app_name, app_data in report['app_coverage'].items():
            coverage_pct = app_data['coverage_percentage']
            status = "✅" if coverage_pct >= 100 else "⚠️" if coverage_pct >= 95 else "❌"
            print(f"{status} {app_name}: {coverage_pct:.1f}%")
            
            # Show module details
            for module_type, module_data in app_data['modules'].items():
                module_cov = module_data['coverage']
                print(f"   └─ {module_type}: {module_cov:.1f}%")
        
        # Missing test files
        if report['missing_test_files']:
            print(f"\n❌ MISSING TEST FILES:")
            print("-" * 50)
            for test_file in report['missing_test_files']:
                print(f"   📄 {test_file}")
        
        # Recommendations
        if report['recommendations']:
            print(f"\n💡 RECOMMENDATIONS:")
            print("-" * 50)
            for i, rec in enumerate(report['recommendations'], 1):
                priority_emoji = "🔴" if rec['priority'] == 'HIGH' else "🟡" if rec['priority'] == 'MEDIUM' else "🟢"
                print(f"{priority_emoji} {rec['description']}")
                print(f"   Action: {rec['action']}")
                if 'files' in rec:
                    for file in rec['files'][:3]:  # Show first 3 files
                        print(f"   - {file}")
                    if len(rec['files']) > 3:
                        print(f"   ... and {len(rec['files']) - 3} more")
                print()
        
        # Final status
        print("="*80)
        if report['summary']['coverage_goal_met']:
            print("🎉 EXCELLENT! 100% coverage achieved!")
        else:
            print("📈 COVERAGE IMPROVEMENT NEEDED")
            print(f"   Current: {summary['overall_coverage_percentage']:.1f}%")
            print(f"   Target: 100.0%")
            print(f"   Gap: {100.0 - summary['overall_coverage_percentage']:.1f}%")
        print("="*80)


def main():
    """Main function to run coverage audit."""
    # Get backend path
    backend_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
    
    # Create auditor
    auditor = TestCoverageAuditor(backend_path)
    
    # Run audit
    report = auditor.run_coverage_analysis()
    
    # Print report
    auditor.print_audit_report(report)
    
    # Save report to file
    report_file = os.path.join(os.path.dirname(__file__), 'coverage_audit_report.json')
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n📄 Detailed report saved to: {report_file}")
    
    # Return appropriate exit code
    return 0 if report['summary']['coverage_goal_met'] else 1


if __name__ == "__main__":
    exit(main())
