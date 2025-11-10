#!/usr/bin/env python3
"""
Plan B - Rendimiento de la capa Worker (videos/min)
Análisis completo según los requisitos del documento

Estrategia:
- Bypass de la web: inyectar directamente mensajes en la cola Celery
- Tamaños de video: 50 MB, 100 MB
- Concurrencia: 1, 2, 4 procesos/hilos por nodo
- Pruebas de saturación y sostenidas
- Métricas: Throughput (videos/min), tiempo medio de servicio
- Verificar estabilidad de cola
"""

import asyncio
import json
import time
import uuid
import os
import sys
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
import redis
from celery import Celery
from celery.result import AsyncResult
import psutil

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# S3 support
try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.warning("boto3 no disponible - no se pueden crear videos de prueba en S3")

class PlanBWorkerTester:
    """Tester completo para Plan B - Worker Capacity"""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis_client = redis.from_url(redis_url)
        
        # Configurar Celery para inyectar tareas
        self.celery_app = Celery(
            'plan_b_tester',
            broker=redis_url,
            backend=redis_url
        )
        self.celery_app.conf.update(
            task_serializer='json',
            accept_content=['json'],
            result_serializer='json',
            timezone='UTC',
            enable_utc=True,
        )
        
        self.results = []
        self.task_ids = []
        
        # S3 configuration for test video creation
        self.s3_bucket_name = "anb-rising-starts-videos-east1"
        self.s3_upload_prefix = "uploads/"
        self.s3_client = None
        if BOTO3_AVAILABLE:
            try:
                # Get AWS credentials from environment
                client_kwargs = {'region_name': 'us-east-1'}
                aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
                aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
                aws_session_token = os.getenv('AWS_SESSION_TOKEN')
                
                if aws_access_key_id and aws_secret_access_key:
                    client_kwargs['aws_access_key_id'] = aws_access_key_id
                    client_kwargs['aws_secret_access_key'] = aws_secret_access_key
                    if aws_session_token:
                        client_kwargs['aws_session_token'] = aws_session_token
                
                self.s3_client = boto3.client('s3', **client_kwargs)
                logger.info("S3 client inicializado para crear videos de prueba")
            except Exception as e:
                logger.warning(f"No se pudo inicializar S3 client: {e}")
    
    def create_test_video_file(self, size_mb: int, output_path: str) -> bool:
        """Crear video MP4 válido del tamaño aproximado especificado usando ffmpeg"""
        try:
            
            # Calcular duración aproximada para alcanzar el tamaño deseado
            # Para un video 720p sin audio, aproximadamente:
            # - 50MB ≈ 30-40 segundos
            # - 100MB ≈ 60-80 segundos
            # Usamos bitrate variable para aproximar el tamaño
            duration_seconds = max(10, size_mb * 0.6)  # Aproximación: 50MB ≈ 30s, 100MB ≈ 60s
            
            # Calcular bitrate para aproximar el tamaño deseado
            # bitrate (kbps) = (size_mb * 8 * 1024) / duration_seconds
            target_bitrate = int((size_mb * 8 * 1024) / duration_seconds)
            
            # Crear video simple con ffmpeg: color sólido con duración específica
            # Usamos un color sólido (rojo) para que sea fácil de procesar
            ffmpeg_cmd = [
                'ffmpeg',
                '-f', 'lavfi',
                '-i', f'color=c=red:s=1280x720:d={int(duration_seconds)}',
                '-c:v', 'libx264',
                '-preset', 'ultrafast',  # Más rápido para pruebas
                '-crf', '23',  # Calidad media
                '-b:v', f'{target_bitrate}k',  # Bitrate para aproximar tamaño
                '-pix_fmt', 'yuv420p',
                '-y',  # Sobrescribir si existe
                output_path
            ]
            
            # Ejecutar ffmpeg
            result = subprocess.run(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120  # Timeout de 2 minutos
            )
            
            if result.returncode != 0:
                logger.error(f"Error ejecutando ffmpeg: {result.stderr.decode()}")
                return False
            
            # Verificar que el archivo existe y tiene un tamaño razonable
            if os.path.exists(output_path):
                actual_size_mb = os.path.getsize(output_path) / (1024 * 1024)
                logger.info(f"Video creado: {output_path} ({actual_size_mb:.1f}MB, objetivo: {size_mb}MB)")
                return True
            else:
                logger.error(f"Video no se creó: {output_path}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout creando video: {output_path}")
            return False
        except FileNotFoundError:
            logger.error("ffmpeg no encontrado. Instala ffmpeg: apt-get install ffmpeg")
            return False
        except Exception as e:
            logger.error(f"Error creando video: {e}")
            return False
    
    def upload_test_video_to_s3(self, video_id: str, video_size_mb: int) -> Optional[str]:
        """Crear y subir video de prueba a S3"""
        if not self.s3_client:
            logger.warning("S3 client no disponible - no se puede subir video de prueba")
            return None
        
        try:
            # Crear video MP4 válido local temporalmente
            local_temp_path = f"/tmp/test_video_{video_id}.mp4"
            if not self.create_test_video_file(video_size_mb, local_temp_path):
                return None
            
            # Subir a S3
            s3_key = f"{self.s3_upload_prefix}{video_id}.mp4"
            with open(local_temp_path, 'rb') as f:
                self.s3_client.put_object(
                    Bucket=self.s3_bucket_name,
                    Key=s3_key,
                    Body=f
                )
            
            # Limpiar archivo local
            if os.path.exists(local_temp_path):
                os.remove(local_temp_path)
            
            s3_path = f"s3://{self.s3_bucket_name}/{s3_key}"
            logger.info(f"Video de prueba subido a S3: {s3_path} ({video_size_mb}MB)")
            return s3_path
        except Exception as e:
            logger.error(f"Error subiendo video de prueba a S3: {e}")
            # Limpiar archivo local si existe
            local_temp_path = f"/tmp/test_video_{video_id}.mp4"
            if os.path.exists(local_temp_path):
                os.remove(local_temp_path)
            return None
    
    def create_test_video_payload(self, video_id: str, video_size_mb: int) -> tuple:
        """
        Crear payload realista para procesamiento de video
        Retorna: (video_id, video_path)
        Nota: En producción, estos archivos deberían existir en S3/local storage
        """
        # Usar el bucket correcto y el prefijo correcto para uploads
        # Bucket: anb-rising-starts-videos-east1
        # Prefijo: uploads/
        video_path = f"s3://anb-rising-starts-videos-east1/uploads/{video_id}.mp4"
        
        return video_id, video_path
    
    def inject_task_to_celery(self, video_id: str, video_path: str) -> str:
        """Inyectar tarea directamente en la cola Celery"""
        try:
            # Enviar tarea a la cola 'video_queue' como lo hace el API
            task = self.celery_app.send_task(
                'app.workers.video_processor.process_video_task',
                args=[video_id, video_path],
                queue='video_queue'
            )
            return task.id
        except Exception as e:
            logger.error(f"Error inyectando tarea: {e}")
            return None
    
    def monitor_queue_size(self) -> int:
        """Monitorear tamaño de la cola Celery en Redis"""
        try:
            # Celery usa diferentes formatos de clave según la versión
            # Formato común: celery@{db}:video_queue
            db = self.redis_client.connection_pool.connection_kwargs.get('db', 0)
            
            # Intentar diferentes formatos de clave de cola
            possible_queue_keys = [
                f"celery@{db}:video_queue",
                f"celery:video_queue",
                f"video_queue",
                f"celery@{db}",
            ]
            
            queue_size = 0
            
            # Buscar en las claves de Celery
            all_keys = self.redis_client.keys("celery*")
            for key in all_keys:
                key_str = key.decode('utf-8') if isinstance(key, bytes) else str(key)
                if 'video_queue' in key_str or 'queue' in key_str.lower():
                    try:
                        size = self.redis_client.llen(key)
                        queue_size += size
                    except:
                        pass
            
            # También verificar directamente las claves de cola
            for queue_key in possible_queue_keys:
                try:
                    size = self.redis_client.llen(queue_key)
                    queue_size += size
                except:
                    pass
            
            return queue_size
        except Exception as e:
            logger.warning(f"Error monitoreando cola: {e}")
            return 0
    
    def check_worker_status(self) -> Dict[str, Any]:
        """Verificar si el worker está procesando tareas"""
        try:
            # Verificar claves de Celery en Redis
            all_celery_keys = self.redis_client.keys("celery*")
            
            # Buscar claves de workers activos
            worker_keys = [k for k in all_celery_keys if b'worker' in k.lower() or b'active' in k.lower()]
            
            # Verificar tamaño de cola
            queue_size = self.monitor_queue_size()
            
            return {
                'total_celery_keys': len(all_celery_keys),
                'worker_keys_found': len(worker_keys),
                'queue_size': queue_size,
                'has_workers': len(worker_keys) > 0
            }
        except Exception as e:
            logger.warning(f"Error verificando estado del worker: {e}")
            return {
                'total_celery_keys': 0,
                'worker_keys_found': 0,
                'queue_size': 0,
                'has_workers': False
            }
    
    def get_system_metrics(self) -> Dict[str, float]:
        """Obtener métricas del sistema"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_usage": cpu_percent,
                "memory_usage": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_usage": disk.percent,
                "disk_available_gb": disk.free / (1024**3)
            }
        except Exception as e:
            logger.warning(f"Error obteniendo métricas: {e}")
            return {
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "memory_available_gb": 0.0,
                "disk_usage": 0.0,
                "disk_available_gb": 0.0
            }
    
    def wait_for_tasks_completion(self, task_ids: List[str], timeout_seconds: int = 600) -> Dict[str, Any]:
        """Esperar a que las tareas se completen y recopilar métricas"""
        start_time = time.time()
        completed_tasks = []
        failed_tasks = []
        processing_times = []
        
        logger.info(f"Monitoreando {len(task_ids)} tareas (timeout: {timeout_seconds}s)...")
        
        # Debug: Verificar algunas tareas en Redis al inicio
        if task_ids:
            sample_task_id = task_ids[0]
            logger.info(f"Debug: Verificando tarea de ejemplo {sample_task_id}...")
            try:
                # Buscar todas las claves relacionadas
                pattern = f"*{sample_task_id}*"
                matching_keys = self.redis_client.keys(pattern)
                logger.info(f"Debug: Claves encontradas en Redis para {sample_task_id}: {len(matching_keys)} claves")
                
                # Verificar también en la cola
                queue_keys = self.redis_client.keys("*video_queue*")
                logger.info(f"Debug: Claves de cola encontradas: {len(queue_keys)} claves")
                if queue_keys:
                    logger.info(f"Debug: Primeras 3 claves de cola: {[k.decode('utf-8') if isinstance(k, bytes) else k for k in queue_keys[:3]]}")
                
                # Verificar todas las claves celery
                all_celery_keys = self.redis_client.keys("celery*")
                logger.info(f"Debug: Total claves celery en Redis: {len(all_celery_keys)}")
                
                if matching_keys:
                    logger.info(f"Debug: Primeras 3 claves: {[k.decode('utf-8') if isinstance(k, bytes) else k for k in matching_keys[:3]]}")
                    # Intentar leer una
                    result_data = self.redis_client.get(matching_keys[0])
                    if result_data:
                        logger.info(f"Debug: Datos encontrados (primeros 200 chars): {str(result_data)[:200]}")
                else:
                    logger.warning(f"Debug: NO se encontraron claves para la tarea {sample_task_id}")
                    logger.warning(f"Debug: Esto puede significar que el worker NO está procesando las tareas")
                    logger.warning(f"Debug: Verifica que el worker esté corriendo y escuchando la cola 'video_queue'")
            except Exception as e:
                logger.warning(f"Debug: Error verificando tarea de ejemplo: {e}")
        
        while time.time() - start_time < timeout_seconds:
            pending = []
            
            for task_id in task_ids:
                if task_id in [t['task_id'] for t in completed_tasks + failed_tasks]:
                    continue
                
                # Método 1: Intentar con AsyncResult
                try:
                    result = AsyncResult(task_id, app=self.celery_app)
                    
                    # Verificar estado directamente
                    state = result.state
                    
                    if state == 'SUCCESS':
                        completed_tasks.append({
                            'task_id': task_id,
                            'status': 'completed',
                            'result': result.result
                        })
                    elif state == 'FAILURE':
                        failed_tasks.append({
                            'task_id': task_id,
                            'status': 'failed',
                            'error': str(result.info) if result.info else 'Unknown error'
                        })
                    elif state in ['PENDING', 'STARTED', 'RETRY']:
                        pending.append(task_id)
                    else:
                        # Estado desconocido, intentar con ready()
                        if result.ready():
                            if result.successful():
                                completed_tasks.append({
                                    'task_id': task_id,
                                    'status': 'completed',
                                    'result': result.result
                                })
                            else:
                                failed_tasks.append({
                                    'task_id': task_id,
                                    'status': 'failed',
                                    'error': str(result.info) if result.info else 'Unknown error'
                                })
                        else:
                            pending.append(task_id)
                except Exception as e:
                    # Método 2: Verificar directamente en Redis
                    try:
                        # Celery almacena resultados con diferentes formatos de clave
                        # Intentar diferentes formatos posibles
                        possible_keys = [
                            f"celery-task-meta-{task_id}",
                            f"celery-task-meta:{task_id}",
                            f"celery-task-meta-{task_id.replace('-', '')}",
                        ]
                        
                        result_data = None
                        for key in possible_keys:
                            result_data = self.redis_client.get(key)
                            if result_data:
                                break
                        
                        # Si no se encuentra con los formatos estándar, buscar por patrón
                        if not result_data:
                            # Buscar todas las claves que contengan el task_id
                            pattern = f"*{task_id}*"
                            matching_keys = self.redis_client.keys(pattern)
                            if matching_keys:
                                result_data = self.redis_client.get(matching_keys[0])
                        
                        if result_data:
                            import json
                            try:
                                # Celery puede almacenar como string JSON o bytes
                                if isinstance(result_data, bytes):
                                    result_data = result_data.decode('utf-8')
                                
                                task_result = json.loads(result_data)
                                status = task_result.get('status', 'PENDING')
                                
                                if status == 'SUCCESS':
                                    completed_tasks.append({
                                        'task_id': task_id,
                                        'status': 'completed',
                                        'result': task_result.get('result')
                                    })
                                elif status == 'FAILURE':
                                    failed_tasks.append({
                                        'task_id': task_id,
                                        'status': 'failed',
                                        'error': str(task_result.get('result', 'Unknown error'))
                                    })
                                else:
                                    pending.append(task_id)
                            except json.JSONDecodeError as je:
                                logger.debug(f"Error parseando JSON para tarea {task_id}: {je}")
                                pending.append(task_id)
                        else:
                            pending.append(task_id)
                    except Exception as e2:
                        logger.debug(f"Error verificando tarea {task_id} en Redis: {e2}")
                        pending.append(task_id)
            
            # Calcular progreso
            total_processed = len(completed_tasks) + len(failed_tasks)
            progress = (total_processed / len(task_ids)) * 100 if task_ids else 0
            
            # Mostrar progreso cada vez que cambie o cada 10 segundos
            elapsed = time.time() - start_time
            if total_processed % 10 == 0 or total_processed == len(task_ids) or int(elapsed) % 10 == 0:
                logger.info(f"Progreso: {total_processed}/{len(task_ids)} tareas ({progress:.1f}%) - Completadas: {len(completed_tasks)}, Fallidas: {len(failed_tasks)}")
            
            if len(pending) == 0:
                break
            
            time.sleep(2)  # Esperar 2 segundos antes de verificar de nuevo
        
        elapsed_time = time.time() - start_time
        
        # Calcular métricas
        total_completed = len(completed_tasks)
        total_failed = len(failed_tasks)
        
        # Estimar tiempo de procesamiento promedio (si tenemos resultados)
        if completed_tasks:
            # Tiempo promedio = tiempo total / número de tareas completadas
            avg_processing_time = elapsed_time / total_completed if total_completed > 0 else 0
        else:
            avg_processing_time = 0
        
        return {
            'total_tasks': len(task_ids),
            'completed': total_completed,
            'failed': total_failed,
            'elapsed_time_seconds': elapsed_time,
            'avg_processing_time_seconds': avg_processing_time,
            'throughput_videos_per_min': (total_completed / elapsed_time * 60) if elapsed_time > 0 else 0,
            'success_rate': (total_completed / len(task_ids) * 100) if task_ids else 0
        }
    
    def run_saturation_test(self, video_size_mb: int, num_workers: int, num_tasks: int = 50) -> Dict[str, Any]:
        """Prueba de saturación: inyectar tareas progresivamente"""
        logger.info(f"\n{'='*60}")
        logger.info(f"PRUEBA DE SATURACIÓN")
        logger.info(f"Tamaño: {video_size_mb}MB | Workers: {num_workers} | Tareas: {num_tasks}")
        logger.info(f"{'='*60}")
        
        # Limpiar métricas
        self.task_ids = []
        
        # Obtener métricas iniciales
        initial_metrics = self.get_system_metrics()
        initial_queue_size = self.monitor_queue_size()
        worker_status = self.check_worker_status()
        
        logger.info(f"Estado inicial - CPU: {initial_metrics['cpu_usage']:.1f}% | "
                    f"Memoria: {initial_metrics['memory_usage']:.1f}% | "
                    f"Cola: {initial_queue_size}")
        logger.info(f"Estado del worker - Claves celery: {worker_status['total_celery_keys']} | "
                    f"Workers activos: {worker_status['has_workers']} | "
                    f"Tamaño cola: {worker_status['queue_size']}")
        
        if not worker_status['has_workers']:
            logger.warning("⚠️  ADVERTENCIA: No se detectaron workers activos en Redis")
            logger.warning("⚠️  Verifica que el worker Celery esté corriendo y escuchando la cola 'video_queue'")
        
        # Crear y subir videos de prueba a S3
        logger.info(f"Creando y subiendo {num_tasks} videos de prueba a S3 ({video_size_mb}MB cada uno)...")
        video_paths = {}
        for i in range(num_tasks):
            video_id = str(uuid.uuid4())
            video_path = self.upload_test_video_to_s3(video_id, video_size_mb)
            if video_path:
                video_paths[video_id] = video_path
            else:
                logger.warning(f"No se pudo crear video de prueba {i+1}/{num_tasks}")
            
            if (i + 1) % 10 == 0:
                logger.info(f"  {i + 1}/{num_tasks} videos creados y subidos...")
        
        if not video_paths:
            logger.error("No se pudieron crear videos de prueba. Abortando prueba.")
            return {
                'test_type': 'saturation',
                'error': 'No se pudieron crear videos de prueba en S3'
            }
        
        logger.info(f"✓ {len(video_paths)} videos de prueba creados y subidos a S3")
        
        # Inyectar tareas progresivamente
        logger.info(f"Inyectando {len(video_paths)} tareas en la cola...")
        start_time = time.time()
        
        for video_id, video_path in video_paths.items():
            task_id = self.inject_task_to_celery(video_id, video_path)
            if task_id:
                self.task_ids.append(task_id)
            
            if len(self.task_ids) % 10 == 0:
                logger.info(f"  {len(self.task_ids)}/{len(video_paths)} tareas inyectadas...")
        
        injection_time = time.time() - start_time
        logger.info(f"✓ {len(self.task_ids)} tareas inyectadas en {injection_time:.2f}s")
        
        # Monitorear procesamiento
        logger.info("Monitoreando procesamiento...")
        metrics = self.wait_for_tasks_completion(self.task_ids, timeout_seconds=600)
        
        # Obtener métricas finales
        final_metrics = self.get_system_metrics()
        final_queue_size = self.monitor_queue_size()
        
        # Calcular estabilidad de cola
        queue_growth = final_queue_size - initial_queue_size
        queue_stable = abs(queue_growth) < 5  # Cola estable si no crece más de 5 tareas
        
        result = {
            'test_type': 'saturation',
            'video_size_mb': video_size_mb,
            'num_workers': num_workers,
            'num_tasks_injected': num_tasks,
            'tasks_completed': metrics['completed'],
            'tasks_failed': metrics['failed'],
            'success_rate': metrics['success_rate'],
            'elapsed_time_seconds': metrics['elapsed_time_seconds'],
            'avg_processing_time_seconds': metrics['avg_processing_time_seconds'],
            'throughput_videos_per_min': metrics['throughput_videos_per_min'],
            'initial_cpu': initial_metrics['cpu_usage'],
            'final_cpu': final_metrics['cpu_usage'],
            'initial_memory': initial_metrics['memory_usage'],
            'final_memory': final_metrics['memory_usage'],
            'initial_queue_size': initial_queue_size,
            'final_queue_size': final_queue_size,
            'queue_growth': queue_growth,
            'queue_stable': queue_stable,
            'bottlenecks': []
        }
        
        # Detectar bottlenecks
        if final_metrics['cpu_usage'] > 90:
            result['bottlenecks'].append('CPU saturado (>90%)')
        if final_metrics['memory_usage'] > 85:
            result['bottlenecks'].append('Memoria saturada (>85%)')
        if not queue_stable:
            result['bottlenecks'].append('Cola creciendo sin control')
        if metrics['throughput_videos_per_min'] < 1:
            result['bottlenecks'].append('Throughput muy bajo (<1 video/min)')
        
        return result
    
    def run_sustained_test(self, video_size_mb: int, num_workers: int, 
                          num_tasks: int, duration_minutes: int = 5) -> Dict[str, Any]:
        """Prueba sostenida: mantener número fijo de tareas en cola"""
        logger.info(f"\n{'='*60}")
        logger.info(f"PRUEBA SOSTENIDA")
        logger.info(f"Tamaño: {video_size_mb}MB | Workers: {num_workers} | "
                   f"Tareas: {num_tasks} | Duración: {duration_minutes} min")
        logger.info(f"{'='*60}")
        
        self.task_ids = []
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        initial_metrics = self.get_system_metrics()
        queue_sizes = []
        throughput_samples = []
        completed_tasks_count = 0
        
        logger.info(f"Iniciando prueba sostenida...")
        
        # Crear y subir videos de prueba a S3
        logger.info(f"Creando y subiendo {num_tasks} videos de prueba a S3 ({video_size_mb}MB cada uno)...")
        video_paths = {}  # Almacenar video_id -> video_path para reutilizar
        for i in range(num_tasks):
            video_id = str(uuid.uuid4())
            video_path = self.upload_test_video_to_s3(video_id, video_size_mb)
            if video_path:
                video_paths[video_id] = video_path
            else:
                logger.warning(f"No se pudo crear video de prueba {i+1}/{num_tasks}")
        
        if not video_paths:
            logger.error("No se pudieron crear videos de prueba. Abortando prueba.")
            return {
                'test_type': 'sustained',
                'error': 'No se pudieron crear videos de prueba en S3'
            }
        
        logger.info(f"✓ {len(video_paths)} videos de prueba creados y subidos a S3")
        
        # Inyectar tareas iniciales
        for video_id, video_path in video_paths.items():
            task_id = self.inject_task_to_celery(video_id, video_path)
            if task_id:
                self.task_ids.append(task_id)
        
        logger.info(f"✓ {len(self.task_ids)} tareas iniciales inyectadas")
        
        # Monitorear durante la duración de la prueba
        last_check_time = start_time
        check_interval = 30  # Verificar cada 30 segundos
        
        while time.time() < end_time:
            current_time = time.time()
            
            # Verificar tareas completadas
            completed = 0
            failed = 0
            for task_id in self.task_ids:
                try:
                    # Método 1: AsyncResult
                    result = AsyncResult(task_id, app=self.celery_app)
                    if result.ready():
                        if result.successful():
                            completed += 1
                        else:
                            failed += 1
                except:
                    # Método 2: Verificar directamente en Redis
                    try:
                        # Intentar diferentes formatos de clave
                        possible_keys = [
                            f"celery-task-meta-{task_id}",
                            f"celery-task-meta:{task_id}",
                        ]
                        
                        result_data = None
                        for key in possible_keys:
                            result_data = self.redis_client.get(key)
                            if result_data:
                                break
                        
                        # Si no se encuentra, buscar por patrón
                        if not result_data:
                            pattern = f"*{task_id}*"
                            matching_keys = self.redis_client.keys(pattern)
                            if matching_keys:
                                result_data = self.redis_client.get(matching_keys[0])
                        
                        if result_data:
                            import json
                            if isinstance(result_data, bytes):
                                result_data = result_data.decode('utf-8')
                            task_result = json.loads(result_data)
                            status = task_result.get('status', 'PENDING')
                            if status == 'SUCCESS':
                                completed += 1
                            elif status == 'FAILURE':
                                failed += 1
                    except:
                        pass
            
            # Mantener número fijo de tareas en cola
            current_queue_size = self.monitor_queue_size()
            queue_sizes.append(current_queue_size)
            
            # Si la cola se vacía, inyectar más tareas
            if current_queue_size < num_tasks * 0.5:  # Si la cola baja del 50%
                tasks_to_add = num_tasks - current_queue_size
                for i in range(tasks_to_add):
                    video_id = str(uuid.uuid4())
                    video_path = self.upload_test_video_to_s3(video_id, video_size_mb)
                    if video_path:
                        task_id = self.inject_task_to_celery(video_id, video_path)
                        if task_id:
                            self.task_ids.append(task_id)
                            video_paths[video_id] = video_path
            
            # Calcular throughput en este intervalo
            if current_time - last_check_time >= check_interval:
                elapsed_minutes = (current_time - start_time) / 60
                current_throughput = completed / elapsed_minutes if elapsed_minutes > 0 else 0
                throughput_samples.append(current_throughput)
                
                metrics = self.get_system_metrics()
                logger.info(f"[{int(elapsed_minutes)}min] Completadas: {completed} | "
                          f"Throughput: {current_throughput:.2f} videos/min | "
                          f"Cola: {current_queue_size} | "
                          f"CPU: {metrics['cpu_usage']:.1f}%")
                
                last_check_time = current_time
            
            time.sleep(5)  # Esperar 5 segundos antes de verificar de nuevo
        
        # Calcular métricas finales
        total_time = time.time() - start_time
        final_metrics = self.get_system_metrics()
        
        # Calcular throughput promedio
        avg_throughput = sum(throughput_samples) / len(throughput_samples) if throughput_samples else 0
        
        # Calcular estabilidad de cola
        if queue_sizes:
            queue_variance = sum((q - sum(queue_sizes)/len(queue_sizes))**2 for q in queue_sizes) / len(queue_sizes)
            queue_stable = queue_variance < 100  # Cola estable si varianza < 100
        else:
            queue_stable = False
        
        result = {
            'test_type': 'sustained',
            'video_size_mb': video_size_mb,
            'num_workers': num_workers,
            'num_tasks': num_tasks,
            'duration_minutes': duration_minutes,
            'total_tasks_processed': completed,
            'elapsed_time_seconds': total_time,
            'avg_throughput_videos_per_min': avg_throughput,
            'initial_cpu': initial_metrics['cpu_usage'],
            'final_cpu': final_metrics['cpu_usage'],
            'initial_memory': initial_metrics['memory_usage'],
            'final_memory': final_metrics['memory_usage'],
            'queue_sizes': queue_sizes,
            'queue_stable': queue_stable,
            'queue_variance': queue_variance if queue_sizes else 0,
            'bottlenecks': []
        }
        
        # Detectar bottlenecks
        if final_metrics['cpu_usage'] > 90:
            result['bottlenecks'].append('CPU saturado (>90%)')
        if final_metrics['memory_usage'] > 85:
            result['bottlenecks'].append('Memoria saturada (>85%)')
        if not queue_stable:
            result['bottlenecks'].append('Cola inestable (varianza alta)')
        
        return result
    
    def run_complete_plan_b(self) -> Dict[str, Any]:
        """Ejecutar análisis completo del Plan B"""
        logger.info(f"\n{'='*80}")
        logger.info("PLAN B - ANÁLISIS COMPLETO DE CAPACIDAD DEL WORKER")
        logger.info(f"{'='*80}")
        
        # Configuraciones según requisitos
        video_sizes = [50, 100]  # MB
        worker_configs = [1, 2, 4]  # procesos/hilos
        
        all_results = {
            'analysis_type': 'plan_b_complete',
            'timestamp': datetime.now().isoformat(),
            'configurations': {
                'video_sizes_mb': video_sizes,
                'worker_configs': worker_configs
            },
            'saturation_results': [],
            'sustained_results': [],
            'capacity_table': []
        }
        
        # Ejecutar pruebas de saturación
        logger.info("\n" + "="*80)
        logger.info("FASE 1: PRUEBAS DE SATURACIÓN")
        logger.info("="*80)
        
        for video_size in video_sizes:
            for num_workers in worker_configs:
                logger.info(f"\nProbando: {video_size}MB con {num_workers} workers")
                
                result = self.run_saturation_test(
                    video_size_mb=video_size,
                    num_workers=num_workers,
                    num_tasks=50  # Inyectar 50 tareas para saturación
                )
                
                all_results['saturation_results'].append(result)
                
                # Mostrar resultado
                logger.info(f"Resultado: {result['throughput_videos_per_min']:.2f} videos/min | "
                          f"Estable: {'SI' if result['queue_stable'] else 'NO'}")
                if result['bottlenecks']:
                    logger.info(f"Bottlenecks: {', '.join(result['bottlenecks'])}")
                
                # Pausa entre pruebas
                logger.info("Pausa de 10 segundos...")
                time.sleep(10)
        
        # Ejecutar pruebas sostenidas
        logger.info("\n" + "="*80)
        logger.info("FASE 2: PRUEBAS SOSTENIDAS")
        logger.info("="*80)
        
        for video_size in video_sizes:
            for num_workers in worker_configs:
                logger.info(f"\nProbando: {video_size}MB con {num_workers} workers")
                
                result = self.run_sustained_test(
                    video_size_mb=video_size,
                    num_workers=num_workers,
                    num_tasks=20,  # Mantener 20 tareas en cola
                    duration_minutes=5
                )
                
                all_results['sustained_results'].append(result)
                
                # Mostrar resultado
                logger.info(f"Resultado: {result['avg_throughput_videos_per_min']:.2f} videos/min | "
                          f"Estable: {'SI' if result['queue_stable'] else 'NO'}")
                if result['bottlenecks']:
                    logger.info(f"Bottlenecks: {', '.join(result['bottlenecks'])}")
                
                # Pausa entre pruebas
                logger.info("Pausa de 10 segundos...")
                time.sleep(10)
        
        # Generar tabla de capacidad
        logger.info("\n" + "="*80)
        logger.info("GENERANDO TABLA DE CAPACIDAD")
        logger.info("="*80)
        
        for video_size in video_sizes:
            for num_workers in worker_configs:
                # Buscar mejor resultado (sustained tiene prioridad)
                sustained_result = next(
                    (r for r in all_results['sustained_results'] 
                     if r['video_size_mb'] == video_size and r['num_workers'] == num_workers),
                    None
                )
                
                saturation_result = next(
                    (r for r in all_results['saturation_results'] 
                     if r['video_size_mb'] == video_size and r['num_workers'] == num_workers),
                    None
                )
                
                if sustained_result:
                    capacity = sustained_result['avg_throughput_videos_per_min']
                    stable = sustained_result['queue_stable']
                elif saturation_result:
                    capacity = saturation_result['throughput_videos_per_min']
                    stable = saturation_result['queue_stable']
                else:
                    capacity = 0
                    stable = False
                
                all_results['capacity_table'].append({
                    'video_size_mb': video_size,
                    'num_workers': num_workers,
                    'capacity_videos_per_min': capacity,
                    'stable': stable
                })
        
        return all_results

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Plan B - Análisis de Capacidad del Worker')
    parser.add_argument('--redis-url', required=True, help='URL de Redis (ej: redis://10.0.132.30:6379/0)')
    parser.add_argument('--output-file', help='Archivo de salida para resultados JSON')
    parser.add_argument('--test-type', choices=['saturation', 'sustained', 'complete'], 
                       default='complete', help='Tipo de prueba a ejecutar')
    parser.add_argument('--video-size', type=int, help='Tamaño de video en MB (solo para tests individuales)')
    parser.add_argument('--num-workers', type=int, help='Número de workers (solo para tests individuales)')
    
    args = parser.parse_args()
    
    # Crear tester
    tester = PlanBWorkerTester(args.redis_url)
    
    # Ejecutar pruebas según tipo
    if args.test_type == 'complete':
        logger.info("Ejecutando análisis completo del Plan B...")
        results = tester.run_complete_plan_b()
    elif args.test_type == 'saturation':
        if not args.video_size or not args.num_workers:
            logger.error("--video-size y --num-workers son requeridos para saturation test")
            sys.exit(1)
        results = tester.run_saturation_test(args.video_size, args.num_workers)
    elif args.test_type == 'sustained':
        if not args.video_size or not args.num_workers:
            logger.error("--video-size y --num-workers son requeridos para sustained test")
            sys.exit(1)
        results = tester.run_sustained_test(args.video_size, args.num_workers, num_tasks=20, duration_minutes=5)
    
    # Guardar resultados
    if not args.output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output_file = f"capacity-planning/plan_b_results_{timestamp}.json"
    
    os.makedirs("capacity-planning", exist_ok=True)
    with open(args.output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Mostrar resumen
    logger.info("\n" + "="*80)
    logger.info("RESUMEN DE RESULTADOS")
    logger.info("="*80)
    
    if 'capacity_table' in results:
        logger.info("\nTABLA DE CAPACIDAD:")
        logger.info(f"{'Tamaño (MB)':<12} {'Workers':<8} {'Capacidad (videos/min)':<20} {'Estable':<8}")
        logger.info("-" * 60)
        for entry in results['capacity_table']:
            stable_str = "SI" if entry['stable'] else "NO"
            logger.info(f"{entry['video_size_mb']:<12} {entry['num_workers']:<8} "
                       f"{entry['capacity_videos_per_min']:<20.2f} {stable_str:<8}")
    
    logger.info(f"\nResultados guardados en: {args.output_file}")
    logger.info("="*80)

if __name__ == "__main__":
    main()
