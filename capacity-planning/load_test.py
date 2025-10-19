#!/usr/bin/env python3
"""
Script de pruebas de carga para ANB Rising Stars Showcase
Implementa los escenarios definidos en el análisis de capacidad
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

class LoadTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def create_test_user(self, user_id: int) -> Dict[str, str]:
        """Crear usuario de prueba"""
        user_data = {
            "email": f"testuser{user_id}@example.com",
            "first_name": f"Test{user_id}",
            "last_name": f"User{user_id}",
            "city": "Bogotá",
            "country": "Colombia",
            "password1": "testpassword123",
            "password2": "testpassword123"
        }
        
        async with self.session.post(f"{self.base_url}/api/auth/signup", json=user_data) as response:
            if response.status == 201:
                data = await response.json()
                return {"token": data["access_token"], "user_id": data["user"]["id"]}
            else:
                # Si el usuario ya existe, intentar login
                login_data = aiohttp.FormData()
                login_data.add_field('username', user_data["email"])
                login_data.add_field('password', user_data["password1"])
                async with self.session.post(f"{self.base_url}/api/auth/login", data=login_data) as login_response:
                    if login_response.status == 200:
                        login_result = await login_response.json()
                        return {"token": login_result["access_token"], "user_id": user_data["email"]}
        return None
    
    async def upload_video(self, token: str, user_id: str) -> Dict[str, Any]:
        """Simular upload de video"""
        start_time = time.time()
        
        # Crear archivo de prueba en memoria
        test_video_content = b"fake video content" * 1000  # ~17KB
        
        headers = {"Authorization": f"Bearer {token}"}
        data = aiohttp.FormData()
        data.add_field('file', test_video_content, filename='test_video.mp4', content_type='video/mp4')
        data.add_field('title', f'Test Video {user_id}')
        
        try:
            async with self.session.post(f"{self.base_url}/api/videos/upload", 
                                       data=data, headers=headers) as response:
                end_time = time.time()
                
                result = {
                    "status_code": response.status,
                    "response_time": end_time - start_time,
                    "success": response.status == 202,
                    "timestamp": datetime.now().isoformat(),
                    "user_id": user_id
                }
                
                if response.status == 202:
                    result["video_id"] = (await response.json()).get("video_id")
                
                return result
                
        except Exception as e:
            return {
                "status_code": 0,
                "response_time": time.time() - start_time,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id
            }
    
    async def get_videos(self, token: str) -> Dict[str, Any]:
        """Obtener lista de videos"""
        start_time = time.time()
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            async with self.session.get(f"{self.base_url}/api/videos/", headers=headers) as response:
                end_time = time.time()
                return {
                    "status_code": response.status,
                    "response_time": end_time - start_time,
                    "success": response.status == 200,
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            return {
                "status_code": 0,
                "response_time": time.time() - start_time,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def vote_video(self, token: str, video_id: str) -> Dict[str, Any]:
        """Votar por un video"""
        start_time = time.time()
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            async with self.session.post(f"{self.base_url}/api/public/vote/{video_id}", 
                                       headers=headers) as response:
                end_time = time.time()
                return {
                    "status_code": response.status,
                    "response_time": end_time - start_time,
                    "success": response.status == 200,
                    "timestamp": datetime.now().isoformat(),
                    "video_id": video_id
                }
        except Exception as e:
            return {
                "status_code": 0,
                "response_time": time.time() - start_time,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "video_id": video_id
            }

class TestScenario:
    def __init__(self, tester: LoadTester):
        self.tester = tester
        self.results = []
    
    async def smoke_test(self, duration_minutes: int = 1):
        """Escenario 1: Prueba de sanidad - 5 usuarios durante 1 minuto"""
        print("Ejecutando Smoke Test - 5 usuarios durante 1 minuto")
        
        users = []
        # Crear 5 usuarios
        for i in range(5):
            user_data = await self.tester.create_test_user(i)
            if user_data:
                users.append(user_data)
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        tasks = []
        while time.time() < end_time:
            for user in users:
                # Simular diferentes acciones
                action = random.choice(['upload', 'get_videos', 'vote'])
                
                if action == 'upload':
                    task = self.tester.upload_video(user['token'], user['user_id'])
                elif action == 'get_videos':
                    task = self.tester.get_videos(user['token'])
                else:
                    # Para vote, necesitaríamos un video_id existente
                    task = self.tester.get_videos(user['token'])
                
                tasks.append(task)
                
                # Ejecutar en lotes de 10
                if len(tasks) >= 10:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    self.results.extend([r for r in results if isinstance(r, dict)])
                    tasks = []
            
            await asyncio.sleep(0.1)  # Pequeña pausa entre iteraciones
        
        # Ejecutar tareas restantes
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            self.results.extend([r for r in results if isinstance(r, dict)])
        
        return self._analyze_results("Smoke Test")
    
    async def ramp_test(self, max_users: int, ramp_duration: int = 3, sustain_duration: int = 5):
        """Escenario 2: Prueba de escalamiento - 0 a X usuarios"""
        print(f"Ejecutando Ramp Test - 0 a {max_users} usuarios")
        
        users = []
        start_time = time.time()
        ramp_end = start_time + ramp_duration * 60
        test_end = ramp_end + sustain_duration * 60
        
        # Crear usuarios gradualmente durante el ramp
        user_creation_interval = (ramp_duration * 60) / max_users
        
        current_users = 0
        while time.time() < test_end:
            # Crear nuevos usuarios durante el ramp
            if time.time() < ramp_end and current_users < max_users:
                user_data = await self.tester.create_test_user(current_users)
                if user_data:
                    users.append(user_data)
                    current_users += 1
                    await asyncio.sleep(user_creation_interval)
            
            # Ejecutar acciones con usuarios actuales
            tasks = []
            for user in users:
                action = random.choice(['upload', 'get_videos'])
                if action == 'upload':
                    task = self.tester.upload_video(user['token'], user['user_id'])
                else:
                    task = self.tester.get_videos(user['token'])
                tasks.append(task)
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                self.results.extend([r for r in results if isinstance(r, dict)])
            
            await asyncio.sleep(0.5)
        
        return self._analyze_results(f"Ramp Test ({max_users} usuarios)")
    
    async def sustained_test(self, users: int, duration_minutes: int = 5):
        """Escenario 3: Prueba sostenida - X usuarios durante Y minutos"""
        print(f"Ejecutando Sustained Test - {users} usuarios durante {duration_minutes} minutos")
        
        # Crear usuarios
        test_users = []
        for i in range(users):
            user_data = await self.tester.create_test_user(i)
            if user_data:
                test_users.append(user_data)
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        while time.time() < end_time:
            tasks = []
            for user in test_users:
                action = random.choice(['upload', 'get_videos'])
                if action == 'upload':
                    task = self.tester.upload_video(user['token'], user['user_id'])
                else:
                    task = self.tester.get_videos(user['token'])
                tasks.append(task)
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                self.results.extend([r for r in results if isinstance(r, dict)])
            
            await asyncio.sleep(0.2)
        
        return self._analyze_results(f"Sustained Test ({users} usuarios)")
    
    def _analyze_results(self, test_name: str) -> Dict[str, Any]:
        """Analizar resultados de las pruebas"""
        if not self.results:
            return {"error": "No results to analyze"}
        
        response_times = [r['response_time'] for r in self.results if 'response_time' in r]
        success_count = sum(1 for r in self.results if r.get('success', False))
        total_requests = len(self.results)
        
        analysis = {
            "test_name": test_name,
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
    parser = argparse.ArgumentParser(description='Load Testing para ANB Rising Stars Showcase')
    parser.add_argument('--url', default='http://localhost:8000', help='Base URL de la API')
    parser.add_argument('--scenario', choices=['smoke', 'ramp', 'sustained', 'all'], 
                       default='all', help='Escenario de prueba a ejecutar')
    parser.add_argument('--users', type=int, default=100, help='Número de usuarios para ramp/sustained')
    parser.add_argument('--duration', type=int, default=5, help='Duración en minutos')
    
    args = parser.parse_args()
    
    async with LoadTester(args.url) as tester:
        scenario = TestScenario(tester)
        
        results = []
        
        if args.scenario in ['smoke', 'all']:
            result = await scenario.smoke_test()
            results.append(result)
            print(f"Smoke Test completado: {result}")
        
        if args.scenario in ['ramp', 'all']:
            result = await scenario.ramp_test(args.users)
            results.append(result)
            print(f"Ramp Test completado: {result}")
        
        if args.scenario in ['sustained', 'all']:
            result = await scenario.sustained_test(args.users, args.duration)
            results.append(result)
            print(f"Sustained Test completado: {result}")
        
        # Guardar resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"capacity-planning/results_{timestamp}.json"
        os.makedirs("capacity-planning", exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Resultados guardados en: {filename}")
        
        # Resumen final
        print("\n" + "="*50)
        print("RESUMEN DE PRUEBAS DE CAPACIDAD")
        print("="*50)
        for result in results:
            if 'test_name' in result:
                print(f"\n{result['test_name']}:")
                print(f"   • Total requests: {result['total_requests']}")
                print(f"   • Success rate: {result['success_rate']:.2f}%")
                print(f"   • P95 response time: {result['p95_response_time']:.3f}s")
                print(f"   • Meets SLO: {'SI' if result['meets_slo'] else 'NO'}")

if __name__ == "__main__":
    asyncio.run(main())
