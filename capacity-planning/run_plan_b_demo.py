#!/usr/bin/env python3
"""
Plan B Demo - Ejecución Rápida del Análisis de Capacidad
Demostración del Plan B con configuraciones reducidas para testing rápido
"""

import json
import time
import redis
from datetime import datetime
import logging

# Importar nuestros módulos
from worker_bypass import WorkerBypass
from worker_saturation_test import WorkerSaturationTester
from worker_sustained_test import WorkerSustainedTester
from simulated_worker import WorkerPool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlanBDemo:
    """Demo del Plan B con configuraciones reducidas"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.bypass = WorkerBypass(redis_url)
        self.saturation_tester = WorkerSaturationTester(redis_url)
        self.sustained_tester = WorkerSustainedTester(redis_url)
        
    def check_redis_connection(self) -> bool:
        """Verificar conexión a Redis"""
        try:
            redis_client = redis.from_url(self.redis_url)
            redis_client.ping()
            logger.info("✓ Redis conectado")
            return True
        except Exception as e:
            logger.error(f"✗ Error conectando a Redis: {e}")
            return False
    
    def run_quick_demo(self) -> dict:
        """Ejecutar demo rápido del Plan B"""
        logger.info("Iniciando demo rápido del Plan B")
        
        if not self.check_redis_connection():
            return {"error": "No se puede conectar a Redis"}
        
        demo_results = {
            "demo_type": "plan_b_quick_demo",
            "timestamp": datetime.now().isoformat(),
            "configurations": {
                "video_sizes_mb": [50],  # Solo 50MB para demo rápido
                "worker_configs": [1, 2],  # Solo 1 y 2 workers
                "duration_minutes": 2  # Solo 2 minutos
            },
            "results": {}
        }
        
        # 1. Demo de bypass de la web con worker simulado
        logger.info("1. Demostrando bypass de la web con worker simulado...")
        try:
            # Limpiar cola
            self.bypass.redis_client.delete("video_processing_queue")
            self.bypass.redis_client.delete("processed_jobs")
            
            # Iniciar worker simulado
            worker_pool = WorkerPool(1, self.redis_url)
            worker_pool.start_workers()
            
            # Inyectar algunos trabajos
            job_ids = self.bypass.inject_jobs_to_queue(5, 50)
            initial_queue_size = self.bypass.monitor_queue_size()
            
            # Esperar a que se procesen
            time.sleep(3)
            
            final_queue_size = self.bypass.monitor_queue_size()
            processed_jobs = self.bypass.redis_client.llen("processed_jobs")
            
            # Obtener estadísticas del worker
            worker_stats = worker_pool.get_pool_stats()
            
            # Detener workers
            worker_pool.stop_workers()
            
            demo_results["results"]["bypass_demo"] = {
                "jobs_injected": len(job_ids),
                "initial_queue_size": initial_queue_size,
                "final_queue_size": final_queue_size,
                "processed_jobs": processed_jobs,
                "worker_stats": worker_stats,
                "status": "success"
            }
            logger.info(f"✓ Inyectados {len(job_ids)} trabajos, procesados: {processed_jobs}")
            
        except Exception as e:
            logger.error(f"✗ Error en bypass demo: {e}")
            demo_results["results"]["bypass_demo"] = {"error": str(e)}
        
        # 2. Demo de saturación (configuración reducida)
        logger.info("2. Demostrando pruebas de saturación...")
        try:
            # Usar configuración reducida para demo
            saturation_result = self.saturation_tester.run_saturation_ramp_test(50, 1)
            
            demo_results["results"]["saturation_demo"] = {
                "max_sustainable_batch": saturation_result["max_sustainable_batch"],
                "max_throughput": saturation_result["max_throughput_videos_per_min"],
                "saturation_point": saturation_result["saturation_point"],
                "bottlenecks": len(saturation_result["bottlenecks"])
            }
            logger.info(f"✓ Saturación: {saturation_result['max_sustainable_batch']} trabajos, "
                       f"{saturation_result['max_throughput_videos_per_min']:.1f} videos/min")
            
        except Exception as e:
            logger.error(f"✗ Error en saturación demo: {e}")
            demo_results["results"]["saturation_demo"] = {"error": str(e)}
        
        # 3. Demo de estabilidad (configuración reducida)
        logger.info("3. Demostrando pruebas de estabilidad...")
        try:
            # Usar configuración reducida para demo
            sustained_result = self.sustained_tester.run_sustained_test(50, 1, 2, 3)
            
            demo_results["results"]["stability_demo"] = {
                "is_stable": sustained_result["stability_analysis"]["is_stable"],
                "throughput": sustained_result["throughput_videos_per_min"],
                "error_rate": sustained_result["stability_analysis"]["error_rate"],
                "cpu_stability": sustained_result["stability_analysis"]["cpu_std"]
            }
            logger.info(f"✓ Estabilidad: {sustained_result['stability_analysis']['is_stable']}, "
                       f"throughput: {sustained_result['throughput_videos_per_min']:.1f} videos/min")
            
        except Exception as e:
            logger.error(f"✗ Error en estabilidad demo: {e}")
            demo_results["results"]["stability_demo"] = {"error": str(e)}
        
        # 4. Generar resumen del demo
        demo_results["summary"] = self._generate_demo_summary(demo_results["results"])
        
        return demo_results
    
    def _generate_demo_summary(self, results: dict) -> dict:
        """Generar resumen del demo"""
        summary = {
            "demo_status": "completed",
            "components_tested": 0,
            "successful_components": 0,
            "failed_components": 0,
            "key_metrics": {},
            "recommendations": []
        }
        
        # Contar componentes
        for component, result in results.items():
            summary["components_tested"] += 1
            if "error" not in result:
                summary["successful_components"] += 1
            else:
                summary["failed_components"] += 1
        
        # Extraer métricas clave
        if "bypass_demo" in results and "error" not in results["bypass_demo"]:
            if "worker_stats" in results["bypass_demo"]:
                worker_stats = results["bypass_demo"]["worker_stats"]
                summary["key_metrics"]["worker_throughput"] = worker_stats.get("throughput_jobs_per_min", 0)
                summary["key_metrics"]["processed_jobs"] = worker_stats.get("total_processed_jobs", 0)
        
        if "saturation_demo" in results and "error" not in results["saturation_demo"]:
            summary["key_metrics"]["max_throughput"] = results["saturation_demo"]["max_throughput"]
            summary["key_metrics"]["saturation_point"] = results["saturation_demo"]["saturation_point"]
        
        if "stability_demo" in results and "error" not in results["stability_demo"]:
            summary["key_metrics"]["is_stable"] = results["stability_demo"]["is_stable"]
            summary["key_metrics"]["error_rate"] = results["stability_demo"]["error_rate"]
        
        # Generar recomendaciones
        if summary["key_metrics"].get("max_throughput", 0) > 0:
            summary["recommendations"].append(
                f"Throughput máximo: {summary['key_metrics']['max_throughput']:.1f} videos/min"
            )
        
        if summary["key_metrics"].get("is_stable", False):
            summary["recommendations"].append("Sistema estable en configuración de prueba")
        else:
            summary["recommendations"].append("Considerar optimizar configuración para mejorar estabilidad")
        
        return summary
    
    def print_demo_summary(self, results: dict):
        """Imprimir resumen del demo"""
        print(f"\n{'='*70}")
        print("DEMO DEL PLAN B - ANÁLISIS DE CAPACIDAD DEL WORKER")
        print(f"{'='*70}")
        
        if "summary" in results:
            summary = results["summary"]
            
            print(f"Estado del demo: {summary['demo_status']}")
            print(f"Componentes probados: {summary['components_tested']}")
            print(f"Componentes exitosos: {summary['successful_components']}")
            print(f"Componentes fallidos: {summary['failed_components']}")
            
            print(f"\n{'='*50}")
            print("MÉTRICAS CLAVE")
            print(f"{'='*50}")
            
            if "worker_throughput" in summary["key_metrics"]:
                print(f"Throughput del worker: {summary['key_metrics']['worker_throughput']:.1f} jobs/min")
            
            if "processed_jobs" in summary["key_metrics"]:
                print(f"Trabajos procesados: {summary['key_metrics']['processed_jobs']}")
            
            if "max_throughput" in summary["key_metrics"]:
                print(f"Throughput máximo: {summary['key_metrics']['max_throughput']:.1f} videos/min")
            
            if "saturation_point" in summary["key_metrics"]:
                print(f"Punto de saturación: {summary['key_metrics']['saturation_point']} trabajos")
            
            if "is_stable" in summary["key_metrics"]:
                stable_str = "Estable" if summary["key_metrics"]["is_stable"] else "Inestable"
                print(f"Estabilidad: {stable_str}")
            
            if "error_rate" in summary["key_metrics"]:
                print(f"Tasa de errores: {summary['key_metrics']['error_rate']:.2%}")
            
            print(f"\n{'='*50}")
            print("RECOMENDACIONES")
            print(f"{'='*50}")
            
            for i, rec in enumerate(summary["recommendations"], 1):
                print(f"{i}. {rec}")
        
        print(f"\n{'='*70}")
        print("DEMO COMPLETADO")
        print(f"{'='*70}")

def main():
    """Función principal del demo"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Plan B Demo - Análisis de Capacidad del Worker")
    parser.add_argument("--redis-url", default="redis://localhost:6379", help="URL de Redis")
    parser.add_argument("--output-file", help="Archivo de salida para resultados")
    
    args = parser.parse_args()
    
    # Crear demo
    demo = PlanBDemo(args.redis_url)
    
    # Ejecutar demo
    logger.info("Iniciando demo del Plan B")
    results = demo.run_quick_demo()
    
    # Guardar resultados
    if args.output_file:
        with open(args.output_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Resultados guardados en: {args.output_file}")
    
    # Imprimir resumen
    demo.print_demo_summary(results)
    
    return results

if __name__ == "__main__":
    main()
