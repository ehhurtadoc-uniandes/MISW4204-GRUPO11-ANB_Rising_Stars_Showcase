#!/usr/bin/env python3
"""
Script simplificado de pruebas de capacidad del worker
"""

import asyncio
import aiohttp
import time
import json
import os
from datetime import datetime
from typing import List, Dict, Any
import statistics
import argparse

class SimpleWorkerTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
    
    async def test_worker_health(self) -> Dict[str, Any]:
        """Probar salud del worker a través de la API"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                # Probar endpoint de health
                async with session.get(f"{self.base_url}/health") as response:
                    end_time = time.time()
                    
                    result = {
                        "test_type": "worker_health",
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
                "test_type": "worker_health",
                "status_code": 0,
                "response_time": time.time() - start_time,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def test_video_upload_simulation(self, num_uploads: int = 10) -> List[Dict[str, Any]]:
        """Simular múltiples uploads de video"""
        results = []
        
        print(f"Simulando {num_uploads} uploads de video...")
        
        for i in range(num_uploads):
            start_time = time.time()
            
            try:
                async with aiohttp.ClientSession() as session:
                    # Crear usuario de prueba
                    user_data = {
                        "email": f"testuser{i}@example.com",
                        "first_name": f"Test{i}",
                        "last_name": f"User{i}",
                        "city": "Bogotá",
                        "country": "Colombia",
                        "password1": "testpassword123",
                        "password2": "testpassword123"
                    }
                    
                    # Intentar signup
                    async with session.post(f"{self.base_url}/api/auth/signup", json=user_data) as signup_response:
                        if signup_response.status == 201:
                            signup_data = await signup_response.json()
                            token = signup_data["access_token"]
                            
                            # Simular upload de video
                            test_video_content = b"fake video content" * 1000  # ~17KB
                            
                            headers = {"Authorization": f"Bearer {token}"}
                            data = aiohttp.FormData()
                            data.add_field('file', test_video_content, filename='test_video.mp4', content_type='video/mp4')
                            data.add_field('title', f'Test Video {i}')
                            
                            async with session.post(f"{self.base_url}/api/videos/upload", 
                                                   data=data, headers=headers) as upload_response:
                                end_time = time.time()
                                
                                result = {
                                    "test_type": "video_upload",
                                    "upload_id": i,
                                    "status_code": upload_response.status,
                                    "response_time": end_time - start_time,
                                    "success": upload_response.status == 202,
                                    "timestamp": datetime.now().isoformat()
                                }
                                
                                if upload_response.status == 202:
                                    upload_data = await upload_response.json()
                                    result["data"] = upload_data
                                
                                results.append(result)
                        else:
                            # Si signup falla, solo registrar el intento
                            end_time = time.time()
                            results.append({
                                "test_type": "video_upload",
                                "upload_id": i,
                                "status_code": signup_response.status,
                                "response_time": end_time - start_time,
                                "success": False,
                                "error": "Signup failed",
                                "timestamp": datetime.now().isoformat()
                            })
                            
            except Exception as e:
                end_time = time.time()
                results.append({
                    "test_type": "video_upload",
                    "upload_id": i,
                    "status_code": 0,
                    "response_time": end_time - start_time,
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
            
            # Pequeña pausa entre uploads
            await asyncio.sleep(0.5)
        
        return results
    
    async def test_sustained_load(self, duration_seconds: int = 60, uploads_per_minute: int = 10):
        """Prueba de carga sostenida"""
        print(f"Ejecutando prueba de carga sostenida: {duration_seconds} segundos, {uploads_per_minute} uploads/min")
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        upload_interval = 60.0 / uploads_per_minute  # Segundos entre uploads
        upload_count = 0
        
        while time.time() < end_time:
            # Simular un upload
            upload_start = time.time()
            
            try:
                async with aiohttp.ClientSession() as session:
                    # Crear usuario único
                    user_id = int(time.time() * 1000) % 10000
                    user_data = {
                        "email": f"sustained{user_id}@example.com",
                        "first_name": f"Sustained{user_id}",
                        "last_name": f"User{user_id}",
                        "city": "Bogotá",
                        "country": "Colombia",
                        "password1": "testpassword123",
                        "password2": "testpassword123"
                    }
                    
                    # Intentar signup y upload
                    async with session.post(f"{self.base_url}/api/auth/signup", json=user_data) as signup_response:
                        if signup_response.status == 201:
                            signup_data = await signup_response.json()
                            token = signup_data["access_token"]
                            
                            # Simular upload
                            test_video_content = b"fake video content" * 1000
                            
                            headers = {"Authorization": f"Bearer {token}"}
                            data = aiohttp.FormData()
                            data.add_field('file', test_video_content, filename='sustained_video.mp4', content_type='video/mp4')
                            data.add_field('title', f'Sustained Video {upload_count}')
                            
                            async with session.post(f"{self.base_url}/api/videos/upload", 
                                                   data=data, headers=headers) as upload_response:
                                upload_end = time.time()
                                
                                result = {
                                    "test_type": "sustained_upload",
                                    "upload_id": upload_count,
                                    "status_code": upload_response.status,
                                    "response_time": upload_end - upload_start,
                                    "success": upload_response.status == 202,
                                    "timestamp": datetime.now().isoformat()
                                }
                                
                                self.results.append(result)
                                upload_count += 1
                        else:
                            # Registrar fallo de signup
                            upload_end = time.time()
                            self.results.append({
                                "test_type": "sustained_upload",
                                "upload_id": upload_count,
                                "status_code": signup_response.status,
                                "response_time": upload_end - upload_start,
                                "success": False,
                                "error": "Signup failed",
                                "timestamp": datetime.now().isoformat()
                            })
                            upload_count += 1
                            
            except Exception as e:
                upload_end = time.time()
                self.results.append({
                    "test_type": "sustained_upload",
                    "upload_id": upload_count,
                    "status_code": 0,
                    "response_time": upload_end - upload_start,
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                upload_count += 1
            
            # Esperar antes del siguiente upload
            await asyncio.sleep(upload_interval)
        
        print(f"Prueba sostenida completada: {upload_count} uploads en {duration_seconds} segundos")
        return self._analyze_results()
    
    def _analyze_results(self) -> Dict[str, Any]:
        """Analizar resultados de las pruebas"""
        if not self.results:
            return {"error": "No results to analyze"}
        
        response_times = [r['response_time'] for r in self.results if 'response_time' in r]
        success_count = sum(1 for r in self.results if r.get('success', False))
        total_requests = len(self.results)
        
        analysis = {
            "total_uploads": total_requests,
            "successful_uploads": success_count,
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
            analysis["p95_response_time"] <= 5.0 and  # Más tiempo para uploads
            analysis["error_rate"] <= 10.0  # Más tolerancia para uploads
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
    parser = argparse.ArgumentParser(description='Simple Worker Testing para ANB Rising Stars Showcase')
    parser.add_argument('--url', default='http://localhost:8000', help='Base URL de la API')
    parser.add_argument('--test-type', choices=['health', 'upload', 'sustained', 'all'], 
                       default='all', help='Tipo de prueba a ejecutar')
    parser.add_argument('--uploads', type=int, default=10, help='Número de uploads para prueba de upload')
    parser.add_argument('--duration', type=int, default=60, help='Duración en segundos para prueba sostenida')
    parser.add_argument('--uploads-per-minute', type=int, default=10, help='Uploads por minuto para prueba sostenida')
    
    args = parser.parse_args()
    
    tester = SimpleWorkerTester(args.url)
    
    results = []
    
    if args.test_type in ['health', 'all']:
        print("Probando salud del worker...")
        result = await tester.test_worker_health()
        results.append(result)
        print(f"Worker health: {result}")
    
    if args.test_type in ['upload', 'all']:
        print("Probando uploads de video...")
        upload_results = await tester.test_video_upload_simulation(args.uploads)
        results.extend(upload_results)
        print(f"Upload tests: {len(upload_results)} tests")
    
    if args.test_type in ['sustained', 'all']:
        print("Ejecutando prueba de carga sostenida...")
        sustained_result = await tester.test_sustained_load(args.duration, args.uploads_per_minute)
        results.append(sustained_result)
        print(f"Sustained test: {sustained_result}")
    
    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"capacity-planning/simple_worker_results_{timestamp}.json"
    os.makedirs("capacity-planning", exist_ok=True)
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Resultados guardados en: {filename}")
    
    # Resumen final
    print("\n" + "="*50)
    print("RESUMEN DE PRUEBAS DEL WORKER")
    print("="*50)
    
    for result in results:
        if 'total_uploads' in result:
            print(f"\nSustained Test:")
            print(f"   • Total uploads: {result['total_uploads']}")
            print(f"   • Success rate: {result['success_rate']:.2f}%")
            print(f"   • P95 response time: {result['p95_response_time']:.3f}s")
            print(f"   • Meets SLO: {'SI' if result['meets_slo'] else 'NO'}")
        else:
            print(f"\n{result.get('test_type', 'Test')}:")
            print(f"   • Status: {result.get('status_code', 'N/A')}")
            print(f"   • Response time: {result.get('response_time', 0):.3f}s")
            print(f"   • Success: {'SI' if result.get('success', False) else 'NO'}")

if __name__ == "__main__":
    asyncio.run(main())
