#!/usr/bin/env python3
"""
Script simplificado de pruebas de carga para ANB Rising Stars Showcase
Versión robusta sin emojis y con manejo de errores mejorado
"""

import asyncio
import aiohttp
import time
import json
import random
import os
from datetime import datetime
from typing import List, Dict, Any
import statistics
import argparse

class SimpleLoadTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        
    async def test_health_endpoint(self) -> Dict[str, Any]:
        """Probar endpoint de health"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    end_time = time.time()
                    
                    result = {
                        "endpoint": "health",
                        "status_code": response.status,
                        "response_time": end_time - start_time,
                        "success": response.status == 200,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    if response.status == 200:
                        data = await response.json()
                        result["data"] = data
                    
                    return result
                    
        except Exception as e:
            return {
                "endpoint": "health",
                "status_code": 0,
                "response_time": time.time() - start_time,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def test_public_endpoints(self) -> List[Dict[str, Any]]:
        """Probar endpoints públicos"""
        results = []
        
        endpoints = [
            "/api/public/videos",
            "/api/public/ranking"
        ]
        
        for endpoint in endpoints:
            start_time = time.time()
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.base_url}{endpoint}") as response:
                        end_time = time.time()
                        
                        result = {
                            "endpoint": endpoint,
                            "status_code": response.status,
                            "response_time": end_time - start_time,
                            "success": response.status == 200,
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        if response.status == 200:
                            data = await response.json()
                            result["data"] = data
                        
                        results.append(result)
                        
            except Exception as e:
                results.append({
                    "endpoint": endpoint,
                    "status_code": 0,
                    "response_time": time.time() - start_time,
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        return results
    
    async def test_auth_endpoints(self) -> List[Dict[str, Any]]:
        """Probar endpoints de autenticación"""
        results = []
        
        # Probar signup
        user_data = {
            "email": f"testuser{int(time.time())}@example.com",
            "first_name": "Test",
            "last_name": "User",
            "city": "Bogotá",
            "country": "Colombia",
            "password1": "testpassword123",
            "password2": "testpassword123"
        }
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/api/auth/signup", json=user_data) as response:
                    end_time = time.time()
                    
                    result = {
                        "endpoint": "signup",
                        "status_code": response.status,
                        "response_time": end_time - start_time,
                        "success": response.status == 201,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    if response.status == 201:
                        data = await response.json()
                        result["data"] = data
                        results.append(result)
                        
                        # Si el signup fue exitoso, probar login
                        login_json = {
                            "email": user_data["email"],
                            "password": user_data["password1"]
                        }
                        
                        login_start = time.time()
                        async with session.post(f"{self.base_url}/api/auth/login", json=login_json) as login_response:
                            login_end = time.time()
                            
                            login_result = {
                                "endpoint": "login",
                                "status_code": login_response.status,
                                "response_time": login_end - login_start,
                                "success": login_response.status == 200,
                                "timestamp": datetime.now().isoformat()
                            }
                            
                            if login_response.status == 200:
                                login_data = await login_response.json()
                                login_result["data"] = login_data
                            
                            results.append(login_result)
                    else:
                        results.append(result)
                        
        except Exception as e:
            results.append({
                "endpoint": "signup",
                "status_code": 0,
                "response_time": time.time() - start_time,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
        
        return results
    
    async def run_load_test(self, duration_seconds: int = 60, requests_per_second: int = 1):
        """Ejecutar prueba de carga básica"""
        print(f"Ejecutando prueba de carga: {duration_seconds} segundos, {requests_per_second} RPS")
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        request_count = 0
        
        while time.time() < end_time:
            # Probar health endpoint
            result = await self.test_health_endpoint()
            self.results.append(result)
            request_count += 1
            
            # Pequeña pausa para controlar RPS
            await asyncio.sleep(1.0 / requests_per_second)
        
        print(f"Prueba completada: {request_count} requests en {duration_seconds} segundos")
        return self._analyze_results()
    
    def _analyze_results(self) -> Dict[str, Any]:
        """Analizar resultados de las pruebas"""
        if not self.results:
            return {"error": "No results to analyze"}
        
        response_times = [r['response_time'] for r in self.results if 'response_time' in r]
        success_count = sum(1 for r in self.results if r.get('success', False))
        total_requests = len(self.results)
        
        analysis = {
            "total_requests": total_requests,
            "successful_requests": success_count,
            "success_rate": (success_count / total_requests) * 100 if total_requests > 0 else 0,
            "avg_response_time": statistics.mean(response_times) if response_times else 0,
            "p95_response_time": self._percentile(response_times, 95) if response_times else 0,
            "p99_response_time": self._percentile(response_times, 99) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
            "min_response_time": min(response_times) if response_times else 0,
            "error_rate": ((total_requests - success_count) / total_requests) * 100 if total_requests > 0 else 0
        }
        
        # Criterios de éxito
        analysis["meets_slo"] = (
            analysis["p95_response_time"] <= 1.0 and
            analysis["error_rate"] <= 5.0
        )
        
        return analysis
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calcular percentil"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]

async def main():
    parser = argparse.ArgumentParser(description='Simple Load Testing para ANB Rising Stars Showcase')
    parser.add_argument('--url', default='http://localhost:8000', help='Base URL de la API')
    parser.add_argument('--duration', type=int, default=60, help='Duración en segundos')
    parser.add_argument('--rps', type=int, default=1, help='Requests por segundo')
    parser.add_argument('--test-type', choices=['health', 'public', 'auth', 'load', 'all'], 
                       default='all', help='Tipo de prueba a ejecutar')
    
    args = parser.parse_args()
    
    tester = SimpleLoadTester(args.url)
    
    results = []
    
    if args.test_type in ['health', 'all']:
        print("Probando endpoint de health...")
        result = await tester.test_health_endpoint()
        results.append(result)
        print(f"Health test: {result}")
    
    if args.test_type in ['public', 'all']:
        print("Probando endpoints públicos...")
        public_results = await tester.test_public_endpoints()
        results.extend(public_results)
        print(f"Public endpoints: {len(public_results)} tests")
    
    if args.test_type in ['auth', 'all']:
        print("Probando endpoints de autenticación...")
        auth_results = await tester.test_auth_endpoints()
        results.extend(auth_results)
        print(f"Auth endpoints: {len(auth_results)} tests")
    
    if args.test_type in ['load', 'all']:
        print("Ejecutando prueba de carga...")
        load_result = await tester.run_load_test(args.duration, args.rps)
        results.append(load_result)
        print(f"Load test: {load_result}")
    
    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"capacity-planning/simple_results_{timestamp}.json"
    os.makedirs("capacity-planning", exist_ok=True)
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Resultados guardados en: {filename}")
    
    # Resumen final
    print("\n" + "="*50)
    print("RESUMEN DE PRUEBAS SIMPLES")
    print("="*50)
    
    for result in results:
        if 'total_requests' in result:
            print(f"\nLoad Test:")
            print(f"   • Total requests: {result['total_requests']}")
            print(f"   • Success rate: {result['success_rate']:.2f}%")
            print(f"   • P95 response time: {result['p95_response_time']:.3f}s")
            print(f"   • Meets SLO: {'SI' if result['meets_slo'] else 'NO'}")
        else:
            print(f"\n{result.get('endpoint', 'Test')}:")
            print(f"   • Status: {result.get('status_code', 'N/A')}")
            print(f"   • Response time: {result.get('response_time', 0):.3f}s")
            print(f"   • Success: {'SI' if result.get('success', False) else 'NO'}")

if __name__ == "__main__":
    asyncio.run(main())
