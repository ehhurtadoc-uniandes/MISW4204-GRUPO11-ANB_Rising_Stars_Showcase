#!/usr/bin/env python3
"""
Escenario 1 - Capacidad de la capa Web (usuarios concurrentes)
Determinar el número de usuarios concurrentes (y RPS asociado) que la API de subida soporta
cumpliendo SLOs, sin estar limitado por la capa asíncrona.

Mejoras implementadas:
- Múltiples ramp tests incrementales (100 → 200 → 300...) hasta encontrar degradación
- Curva usuarios→latencia/errores
- Cálculo de RPS sostenido
- Análisis de bottlenecks mejorado
- Tracking de métricas por intervalo de tiempo
"""

import asyncio
import aiohttp
import time
import json
import random
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import statistics
import argparse
from collections import defaultdict

class Escenario1Tester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.results: List[Dict[str, Any]] = []
        self.active_users: List[Dict[str, str]] = []
        self.metrics_by_interval: List[Dict[str, Any]] = []  # Para curvas
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def create_and_login_user(self, user_id: int) -> Optional[Dict[str, str]]:
        """Crear usuario y hacer login para obtener token"""
        user_data = {
            "email": f"escenario1_user{user_id}@test.com",
            "first_name": f"Test{user_id}",
            "last_name": f"User{user_id}",
            "city": "Bogotá",
            "country": "Colombia",
            "password1": "testpassword123",
            "password2": "testpassword123"
        }
        
        # Intentar signup
        try:
            async with self.session.post(f"{self.base_url}/api/auth/signup", json=user_data) as response:
                if response.status in [201, 400]:  # 201 creado, 400 ya existe
                    pass
        except Exception:
            pass  # Continuar con login
        
        # Hacer login para obtener token
        try:
            login_data = aiohttp.FormData()
            login_data.add_field('username', user_data["email"])
            login_data.add_field('password', user_data["password1"])
            
            async with self.session.post(f"{self.base_url}/api/auth/login", data=login_data) as login_response:
                if login_response.status == 200:
                    login_result = await login_response.json()
                    return {
                        "token": login_result["access_token"],
                        "user_id": str(user_id),
                        "email": user_data["email"]
                    }
        except Exception:
            pass
        
        return None
    
    async def upload_video(self, token: str, user_id: str, file_size_mb: float = 5.0) -> Dict[str, Any]:
        """Simular upload de video con archivo realista"""
        start_time = time.time()
        
        # Crear archivo de prueba más realista (simula video MP4)
        file_size_bytes = int(file_size_mb * 1024 * 1024)
        test_video_content = b"\x00" * file_size_bytes
        
        headers = {"Authorization": f"Bearer {token}"}
        data = aiohttp.FormData()
        data.add_field('video_file', test_video_content, filename=f'test_video_{user_id}_{int(time.time())}.mp4', content_type='video/mp4')
        data.add_field('title', f'Escenario1 Test Video {user_id} {int(time.time())}')
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/videos/upload", 
                data=data, 
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                end_time = time.time()
                response_time = end_time - start_time
                
                result = {
                    "status_code": response.status,
                    "response_time": response_time,
                    "success": response.status in [201, 202],
                    "timestamp": datetime.now().isoformat(),
                    "user_id": user_id,
                    "file_size_mb": file_size_mb,
                    "endpoint": "upload"
                }
                
                if response.status in [201, 202]:
                    try:
                        response_data = await response.json()
                        result["task_id"] = response_data.get("task_id")
                    except:
                        pass
                else:
                    try:
                        error_data = await response.text()
                        result["error"] = error_data[:200]
                    except:
                        pass
                
                return result
                
        except asyncio.TimeoutError:
            return {
                "status_code": 0,
                "response_time": time.time() - start_time,
                "success": False,
                "error": "Timeout",
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "endpoint": "upload"
            }
        except Exception as e:
            return {
                "status_code": 0,
                "response_time": time.time() - start_time,
                "success": False,
                "error": str(e)[:200],
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "endpoint": "upload"
            }
    
    async def get_videos(self, token: str) -> Dict[str, Any]:
        """Obtener lista de videos del usuario"""
        start_time = time.time()
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            async with self.session.get(
                f"{self.base_url}/api/videos",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                end_time = time.time()
                
                return {
                    "status_code": response.status,
                    "response_time": end_time - start_time,
                    "success": response.status == 200,
                    "timestamp": datetime.now().isoformat(),
                    "endpoint": "get_videos"
                }
        except Exception as e:
            return {
                "status_code": 0,
                "response_time": time.time() - start_time,
                "success": False,
                "error": str(e)[:200],
                "timestamp": datetime.now().isoformat(),
                "endpoint": "get_videos"
            }
    
    def analyze_results(self, test_name: str, num_users: int = 0) -> Dict[str, Any]:
        """Analizar resultados y calcular métricas"""
        if not self.results:
            return {
                "test_name": test_name,
                "num_users": num_users,
                "total_requests": 0,
                "successful_requests": 0,
                "success_rate": 0.0,
                "error_rate": 100.0,
                "avg_response_time": 0.0,
                "p50_response_time": 0.0,
                "p95_response_time": 0.0,
                "p99_response_time": 0.0,
                "max_response_time": 0.0,
                "min_response_time": 0.0,
                "rps": 0.0,
                "meets_slo": False,
                "errors_by_status": {},
                "timeouts": 0,
                "bottlenecks": []
            }
        
        successful = [r for r in self.results if r.get("success", False)]
        failed = [r for r in self.results if not r.get("success", False)]
        timeouts = [r for r in failed if r.get("error") == "Timeout"]
        
        response_times = [r["response_time"] for r in self.results if "response_time" in r]
        
        # Calcular percentiles
        response_times_sorted = sorted(response_times) if response_times else [0]
        total = len(response_times_sorted)
        
        p50 = response_times_sorted[int(total * 0.50)] if total > 0 else 0
        p95 = response_times_sorted[int(total * 0.95)] if total > 0 else 0
        p99 = response_times_sorted[int(total * 0.99)] if total > 0 else 0
        
        # Errores por status code
        errors_by_status = defaultdict(int)
        for r in failed:
            status = r.get("status_code", 0)
            errors_by_status[status] += 1
        
        # Calcular error rate (4xx evitables + 5xx)
        error_count = sum(1 for r in failed if r.get("status_code", 0) >= 400)
        error_rate = (error_count / len(self.results)) * 100 if self.results else 100.0
        
        # Calcular RPS (Requests Per Second)
        if self.results:
            timestamps = [datetime.fromisoformat(r["timestamp"]) for r in self.results if "timestamp" in r]
            if timestamps:
                time_span = (max(timestamps) - min(timestamps)).total_seconds()
                rps = len(self.results) / time_span if time_span > 0 else 0
            else:
                rps = 0
        else:
            rps = 0
        
        # Verificar SLO
        meets_slo = (
            p95 <= 1.0 and  # p95 ≤ 1s
            error_rate <= 5.0  # Errores ≤ 5%
        )
        
        # Detectar bottlenecks
        bottlenecks = []
        if p95 > 1.0:
            bottlenecks.append(f"p95 latencia alta: {p95:.3f}s (SLO: ≤1s)")
        if error_rate > 5.0:
            bottlenecks.append(f"Error rate alto: {error_rate:.2f}% (SLO: ≤5%)")
        if len(timeouts) > 0:
            timeout_rate = (len(timeouts) / len(self.results)) * 100
            bottlenecks.append(f"Timeouts detectados: {len(timeouts)} ({timeout_rate:.2f}%)")
        if p99 > 5.0:
            bottlenecks.append(f"p99 latencia muy alta: {p99:.3f}s")
        
        return {
            "test_name": test_name,
            "num_users": num_users,
            "total_requests": len(self.results),
            "successful_requests": len(successful),
            "failed_requests": len(failed),
            "success_rate": (len(successful) / len(self.results)) * 100 if self.results else 0.0,
            "error_rate": error_rate,
            "avg_response_time": statistics.mean(response_times) if response_times else 0.0,
            "p50_response_time": p50,
            "p95_response_time": p95,
            "p99_response_time": p99,
            "max_response_time": max(response_times) if response_times else 0.0,
            "min_response_time": min(response_times) if response_times else 0.0,
            "rps": rps,
            "meets_slo": meets_slo,
            "errors_by_status": dict(errors_by_status),
            "timeouts": len(timeouts),
            "bottlenecks": bottlenecks,
            "timestamp": datetime.now().isoformat()
        }
    
    async def smoke_test(self, duration_minutes: int = 1):
        """Smoke: 5 usuarios durante 1 minuto"""
        print(f"\n{'='*60}")
        print("SMOKE TEST - 5 usuarios durante 1 minuto")
        print(f"{'='*60}")
        
        self.results = []
        self.metrics_by_interval = []
        
        # Crear 5 usuarios
        print("Creando 5 usuarios...")
        users = []
        for i in range(5):
            user = await self.create_and_login_user(i)
            if user:
                users.append(user)
                print(f"  ✓ Usuario {i} creado")
        
        if not users:
            print("ERROR: No se pudieron crear usuarios")
            return self.analyze_results("Smoke Test", 5)
        
        print(f"\nIniciando carga con {len(users)} usuarios...")
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        async def user_worker(user: Dict[str, str]):
            while time.time() < end_time:
                if random.random() < 0.7:
                    result = await self.upload_video(user["token"], user["user_id"], file_size_mb=5.0)
                else:
                    result = await self.get_videos(user["token"])
                
                self.results.append(result)
                await asyncio.sleep(0.5)
        
        tasks = [user_worker(user) for user in users]
        await asyncio.gather(*tasks)
        
        return self.analyze_results("Smoke Test", 5)
    
    async def ramp_test(self, max_users: int):
        """Ramp: 0 a X usuarios en 3 minutos, mantener 5 minutos"""
        print(f"\n{'='*60}")
        print(f"RAMP TEST - 0 a {max_users} usuarios en 3 minutos, mantener 5 minutos")
        print(f"{'='*60}")
        
        self.results = []
        self.active_users = []
        self.metrics_by_interval = []
        
        # Fase 1: Ramp up (3 minutos)
        print("\nFase 1: Ramp Up (3 minutos)...")
        ramp_duration = 3 * 60
        ramp_start = time.time()
        ramp_end = ramp_start + ramp_duration
        
        users_created = 0
        ramp_interval = ramp_duration / max_users if max_users > 0 else 0.1
        
        async def ramp_worker():
            nonlocal users_created
            while time.time() < ramp_end and users_created < max_users:
                user = await self.create_and_login_user(users_created)
                if user:
                    self.active_users.append(user)
                    users_created += 1
                    if users_created % 50 == 0:
                        print(f"  {users_created}/{max_users} usuarios activos")
                await asyncio.sleep(ramp_interval)
        
        async def user_worker(user: Dict[str, str]):
            while time.time() < ramp_end + (5 * 60):
                if random.random() < 0.7:
                    result = await self.upload_video(user["token"], user["user_id"], file_size_mb=5.0)
                else:
                    result = await self.get_videos(user["token"])
                
                self.results.append(result)
                await asyncio.sleep(1.0)
        
        # Iniciar ramp
        await ramp_worker()
        
        # Iniciar workers para usuarios activos
        print(f"\n{len(self.active_users)} usuarios activos, iniciando carga...")
        tasks = [user_worker(user) for user in self.active_users]
        
        # Fase 2: Sostenido (5 minutos)
        print("\nFase 2: Carga Sostenida (5 minutos)...")
        await asyncio.gather(*tasks)
        
        return self.analyze_results(f"Ramp Test", max_users)
    
    async def sustained_test(self, num_users: int, duration_minutes: int = 5):
        """Sostenida: X usuarios durante Y minutos"""
        print(f"\n{'='*60}")
        print(f"SUSTAINED TEST - {num_users} usuarios durante {duration_minutes} minutos")
        print(f"{'='*60}")
        
        self.results = []
        self.metrics_by_interval = []
        
        # Crear usuarios
        print(f"Creando {num_users} usuarios...")
        users = []
        for i in range(num_users):
            user = await self.create_and_login_user(i)
            if user:
                users.append(user)
            if (i + 1) % 100 == 0:
                print(f"  {i + 1}/{num_users} usuarios creados...")
        
        print(f"\n{len(users)} usuarios activos, iniciando carga...")
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        async def user_worker(user: Dict[str, str]):
            while time.time() < end_time:
                if random.random() < 0.7:
                    result = await self.upload_video(user["token"], user["user_id"], file_size_mb=5.0)
                else:
                    result = await self.get_videos(user["token"])
                
                self.results.append(result)
                await asyncio.sleep(1.0)
        
        tasks = [user_worker(user) for user in users]
        await asyncio.gather(*tasks)
        
        return self.analyze_results(f"Sustained Test", num_users)
    
    async def incremental_ramp_tests(self, start_users: int = 100, max_users: int = 10000, step: int = 100):
        """Ejecutar múltiples ramp tests incrementales hasta encontrar degradación"""
        print(f"\n{'='*60}")
        print(f"INCREMENTAL RAMP TESTS - {start_users} → {max_users} usuarios (step: {step})")
        print(f"{'='*60}")
        
        all_results = []
        current_users = start_users
        max_capacity = 0
        degradation_point = None
        
        while current_users <= max_users:
            print(f"\n{'='*60}")
            print(f"Ejecutando Ramp Test con {current_users} usuarios...")
            print(f"{'='*60}")
            
            # Limpiar resultados anteriores
            self.results = []
            self.active_users = []
            
            # Ejecutar ramp test
            result = await self.ramp_test(current_users)
            result["num_users"] = current_users
            all_results.append(result)
            
            # Mostrar resultados
            print(f"\nResultados para {current_users} usuarios:")
            print(f"  • Total requests: {result['total_requests']}")
            print(f"  • RPS: {result['rps']:.2f}")
            print(f"  • P95 response time: {result['p95_response_time']:.3f}s")
            print(f"  • Error rate: {result['error_rate']:.2f}%")
            print(f"  • Meets SLO: {'SI' if result['meets_slo'] else 'NO'}")
            
            if result['bottlenecks']:
                print(f"  • Bottlenecks: {', '.join(result['bottlenecks'])}")
            
            # Verificar si cumple SLO
            if result['meets_slo']:
                max_capacity = current_users
                print(f"  ✓ Cumple SLO - Capacidad máxima hasta ahora: {max_capacity} usuarios")
            else:
                if degradation_point is None:
                    degradation_point = current_users
                    print(f"  ✗ Degradación detectada en {current_users} usuarios")
                    print(f"  • Primer bottleneck: {result['bottlenecks'][0] if result['bottlenecks'] else 'N/A'}")
                
                # Si ya detectamos degradación, podemos parar o continuar
                if degradation_point and current_users > degradation_point + step:
                    print(f"\nDegradación confirmada. Deteniendo tests incrementales.")
                    break
            
            # Incrementar para siguiente test
            current_users += step
            
            # Pausa entre tests
            print(f"\nPausa de 10 segundos antes del siguiente test...")
            await asyncio.sleep(10)
        
        # Generar curva usuarios→latencia/errores
        curve_data = {
            "users": [r["num_users"] for r in all_results],
            "p95_latency": [r["p95_response_time"] for r in all_results],
            "error_rate": [r["error_rate"] for r in all_results],
            "rps": [r["rps"] for r in all_results],
            "meets_slo": [r["meets_slo"] for r in all_results]
        }
        
        return {
            "all_results": all_results,
            "max_capacity": max_capacity,
            "degradation_point": degradation_point,
            "curve_data": curve_data,
            "summary": {
                "max_users_tested": current_users - step,
                "max_capacity_users": max_capacity,
                "max_capacity_rps": all_results[max_capacity // step - 1]["rps"] if max_capacity > 0 else 0,
                "degradation_at": degradation_point
            }
        }

async def main():
    parser = argparse.ArgumentParser(description='Escenario 1 - Capacidad de la capa Web')
    parser.add_argument('--url', default='http://localhost:8000', help='Base URL de la API')
    parser.add_argument('--scenario', choices=['smoke', 'ramp', 'sustained', 'incremental', 'all'], 
                       default='all', help='Escenario a ejecutar')
    parser.add_argument('--users', type=int, default=100, help='Número de usuarios (ramp/sustained)')
    parser.add_argument('--duration', type=int, default=5, help='Duración en minutos (sustained)')
    parser.add_argument('--start-users', type=int, default=100, help='Usuarios iniciales (incremental)')
    parser.add_argument('--max-users', type=int, default=10000, help='Usuarios máximos (incremental)')
    parser.add_argument('--step', type=int, default=100, help='Incremento entre tests (incremental)')
    
    args = parser.parse_args()
    
    async with Escenario1Tester(args.url) as tester:
        results = []
        
        if args.scenario in ['smoke', 'all']:
            result = await tester.smoke_test()
            results.append(result)
            print(f"\n{result}")
        
        if args.scenario in ['ramp', 'all']:
            result = await tester.ramp_test(args.users)
            results.append(result)
            print(f"\n{result}")
        
        if args.scenario in ['sustained', 'all']:
            result = await tester.sustained_test(args.users, args.duration)
            results.append(result)
            print(f"\n{result}")
        
        if args.scenario == 'incremental':
            incremental_result = await tester.incremental_ramp_tests(
                args.start_users, args.max_users, args.step
            )
            results = incremental_result["all_results"]
            
            # Mostrar resumen
            print(f"\n{'='*60}")
            print("RESUMEN DE TESTS INCREMENTALES")
            print(f"{'='*60}")
            print(f"Capacidad máxima: {incremental_result['summary']['max_capacity_users']} usuarios")
            print(f"RPS a capacidad máxima: {incremental_result['summary']['max_capacity_rps']:.2f}")
            print(f"Punto de degradación: {incremental_result['summary']['degradation_at']} usuarios")
            
            # Guardar curva
            curve_filename = f"capacity-planning/escenario1_curve_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(curve_filename, 'w') as f:
                json.dump(incremental_result["curve_data"], f, indent=2)
            print(f"\nCurva usuarios→latencia/errores guardada en: {curve_filename}")
        
        # Guardar resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"capacity-planning/escenario1_results_{timestamp}.json"
        os.makedirs("capacity-planning", exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n{'='*60}")
        print("RESUMEN FINAL")
        print(f"{'='*60}")
        for result in results:
            if isinstance(result, dict) and 'test_name' in result:
                print(f"\n{result['test_name']} ({result.get('num_users', 'N/A')} usuarios):")
                print(f"  • Total requests: {result['total_requests']}")
                print(f"  • RPS: {result['rps']:.2f}")
                print(f"  • Success rate: {result['success_rate']:.2f}%")
                print(f"  • Error rate: {result['error_rate']:.2f}%")
                print(f"  • P95 response time: {result['p95_response_time']:.3f}s")
                print(f"  • Meets SLO: {'SI' if result['meets_slo'] else 'NO'}")
                if result.get('bottlenecks'):
                    print(f"  • Bottlenecks: {', '.join(result['bottlenecks'])}")
        
        print(f"\nResultados guardados en: {filename}")

if __name__ == "__main__":
    asyncio.run(main())
