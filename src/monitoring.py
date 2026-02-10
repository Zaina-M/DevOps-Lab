"""Pipeline Monitoring and Metrics Module

Tracks pipeline execution metrics including success rates,
processing times, error counts, and throughput.
"""

import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collect and aggregate pipeline metrics"""
    
    def __init__(self):
        """Initialize metrics collector"""
        self.metrics = defaultdict(list)
        self.start_time = None
        self.end_time = None
        self.records_processed = 0
        self.records_failed = 0
        self.source_metrics = defaultdict(dict)
    
    def start_pipeline(self) -> None:
        """Mark pipeline start"""
        self.start_time = time.time()
        self.metrics["pipeline_starts"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "start_time": self.start_time
        })
    
    def end_pipeline(self) -> None:
        """Mark pipeline end"""
        self.end_time = time.time()
        duration = self.end_time - self.start_time if self.start_time else 0
        
        self.metrics["pipeline_completions"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "end_time": self.end_time,
            "duration_seconds": duration
        })
    
    def record_ingestion(self, source: str, success: bool, duration: float = 0) -> None:
        """Record ingestion metrics
        
        Args:
            source: Data source name
            success: Whether ingestion succeeded
            duration: Time taken in seconds
        """
        if success:
            self.records_processed += 1
        else:
            self.records_failed += 1
        
        self.metrics["ingestions"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "source": source,
            "success": success,
            "duration_seconds": duration
        })
        
        # Update source-specific metrics
        if source not in self.source_metrics:
            self.source_metrics[source] = {
                "success_count": 0,
                "failure_count": 0,
                "total_duration": 0,
                "record_count": 0
            }
        
        if success:
            self.source_metrics[source]["success_count"] += 1
        else:
            self.source_metrics[source]["failure_count"] += 1
        
        self.source_metrics[source]["total_duration"] += duration
        self.source_metrics[source]["record_count"] += 1
    
    def record_validation(self, valid: bool, errors: List[str] = None) -> None:
        """Record validation metrics
        
        Args:
            valid: Whether validation passed
            errors: List of validation errors
        """
        self.metrics["validations"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "valid": valid,
            "error_count": len(errors) if errors else 0
        })
    
    def record_quality_score(self, score: float) -> None:
        """Record data quality score
        
        Args:
            score: Quality score (0-100)
        """
        self.metrics["quality_scores"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "score": score
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary
        
        Returns:
            Dictionary with aggregated metrics
        """
        duration = (self.end_time - self.start_time) if (self.start_time and self.end_time) else 0
        
        # Calculate success rate
        total_records = self.records_processed + self.records_failed
        success_rate = (self.records_processed / total_records * 100) if total_records > 0 else 0
        
        # Calculate average processing time
        ingestions = self.metrics.get("ingestions", [])
        avg_duration = (
            sum(i["duration_seconds"] for i in ingestions) / len(ingestions)
            if ingestions else 0
        )
        
        # Calculate validation metrics
        validations = self.metrics.get("validations", [])
        valid_count = sum(1 for v in validations if v["valid"])
        validation_rate = (valid_count / len(validations) * 100) if validations else 0
        
        # Calculate average quality score
        quality_scores = self.metrics.get("quality_scores", [])
        avg_quality = (
            sum(q["score"] for q in quality_scores) / len(quality_scores)
            if quality_scores else 0
        )
        
        return {
            "pipeline": {
                "total_duration_seconds": round(duration, 2),
                "start_time": datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None,
                "end_time": datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None
            },
            "records": {
                "total_processed": self.records_processed,
                "total_failed": self.records_failed,
                "success_rate_percent": round(success_rate, 2)
            },
            "ingestion": {
                "total_ingestions": len(ingestions),
                "average_duration_seconds": round(avg_duration, 4),
                "source_breakdown": dict(self.source_metrics)
            },
            "validation": {
                "total_validations": len(validations),
                "valid_count": valid_count,
                "validation_rate_percent": round(validation_rate, 2)
            },
            "quality": {
                "average_score": round(avg_quality, 2),
                "total_scores_recorded": len(quality_scores)
            }
        }
    
    def export_metrics(self, filepath: str) -> None:
        """Export metrics to JSON file
        
        Args:
            filepath: Path to export file
        """
        summary = self.get_summary()
        summary["raw_metrics"] = dict(self.metrics)
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Metrics exported to {filepath}")


class PipelineMonitor:
    """Monitor pipeline health and performance"""
    
    def __init__(self, config: Optional[Any] = None):
        """Initialize pipeline monitor
        
        Args:
            config: Configuration manager (optional)
        """
        self.config = config
        self.metrics_collector = MetricsCollector()
        self.alerts = []
        self.thresholds = {
            "min_success_rate": 95.0,
            "max_avg_duration": 60.0,
            "min_quality_score": 80.0
        }
    
    def check_health(self) -> Dict[str, Any]:
        """Check pipeline health against thresholds
        
        Returns:
            Health check results with status and issues
        """
        summary = self.metrics_collector.get_summary()
        issues = []
        
        # Check success rate
        success_rate = summary["records"]["success_rate_percent"]
        if success_rate < self.thresholds["min_success_rate"]:
            issues.append({
                "severity": "high",
                "metric": "success_rate",
                "value": success_rate,
                "threshold": self.thresholds["min_success_rate"],
                "message": f"Success rate {success_rate}% below threshold {self.thresholds['min_success_rate']}%"
            })
        
        # Check average processing time
        avg_duration = summary["ingestion"]["average_duration_seconds"]
        if avg_duration > self.thresholds["max_avg_duration"]:
            issues.append({
                "severity": "medium",
                "metric": "avg_duration",
                "value": avg_duration,
                "threshold": self.thresholds["max_avg_duration"],
                "message": f"Average duration {avg_duration}s exceeds threshold {self.thresholds['max_avg_duration']}s"
            })
        
        # Check quality score
        avg_quality = summary["quality"]["average_score"]
        if avg_quality > 0 and avg_quality < self.thresholds["min_quality_score"]:
            issues.append({
                "severity": "high",
                "metric": "quality_score",
                "value": avg_quality,
                "threshold": self.thresholds["min_quality_score"],
                "message": f"Quality score {avg_quality} below threshold {self.thresholds['min_quality_score']}"
            })
        
        status = "healthy" if not issues else "degraded" if all(i["severity"] == "medium" for i in issues) else "unhealthy"
        
        health_result = {
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "issues": issues,
            "summary": summary
        }
        
        # Generate alerts for critical issues
        for issue in issues:
            if issue["severity"] == "high":
                self.generate_alert(issue)
        
        return health_result
    
    def generate_alert(self, issue: Dict[str, Any]) -> None:
        """Generate alert for critical issue
        
        Args:
            issue: Issue dictionary with details
        """
        alert = {
            "timestamp": datetime.utcnow().isoformat(),
            "severity": issue["severity"],
            "metric": issue["metric"],
            "message": issue["message"],
            "value": issue["value"],
            "threshold": issue["threshold"]
        }
        
        self.alerts.append(alert)
        logger.warning(f"ALERT: {alert['message']}")
    
    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get all generated alerts
        
        Returns:
            List of alert dictionaries
        """
        return self.alerts
    
    def set_threshold(self, metric: str, value: float) -> None:
        """Set custom threshold for monitoring
        
        Args:
            metric: Metric name
            value: Threshold value
        """
        self.thresholds[metric] = value
        logger.info(f"Threshold set: {metric} = {value}")
