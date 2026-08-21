"""Dynamic Task Graph Scheduler executing multi-agent workflows with parallel branches."""

import asyncio
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.hive.blackboard import blackboard
from mitchell.hive.router import HiveRouter, hive_router
from mitchell.manager.planner import TaskGraph, TaskNode


class WorkflowExecutionResult(BaseModel):
    """Result summary of a TaskGraph workflow execution."""

    plan_id: str
    goal: str
    success: bool
    duration_s: float
    nodes_completed: int
    nodes_failed: int
    node_results: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class TaskGraphScheduler:
    """Schedules and executes dependent TaskGraph nodes across Hive agents."""

    def __init__(self, router: Optional[HiveRouter] = None) -> None:
        self.hive = router or hive_router
        self.board = blackboard

    async def execute_graph(self, graph: TaskGraph) -> WorkflowExecutionResult:
        """Execute a TaskGraph resolving dependencies and running ready tasks."""
        start_time = time.time()
        logger.info("TaskGraphScheduler: Starting execution of TaskGraph '{}' ({} nodes)", graph.id, len(graph.nodes))

        event_log.log_event(
            "workflow_started",
            source="task_scheduler",
            data={"plan_id": graph.id, "goal": graph.goal, "total_nodes": len(graph.nodes)},
        )

        completed_node_ids: Set[str] = set()
        failed_node_ids: Set[str] = set()
        node_results: Dict[str, Any] = {}

        # Post initial workflow notice to Blackboard
        self.board.post(
            topic=f"workflow:{graph.id}",
            content={"status": "running", "goal": graph.goal},
            author="task_scheduler",
        )

        remaining_nodes = {node.id: node for node in graph.nodes}

        while remaining_nodes:
            # Find nodes whose dependencies are all completed
            ready_nodes = [
                node for node in remaining_nodes.values()
                if all(dep in completed_node_ids for dep in node.dependencies)
            ]

            if not ready_nodes:
                # Deadlock / unmet dependencies
                error_msg = f"Deadlock or unresolvable dependencies in remaining nodes: {list(remaining_nodes.keys())}"
                logger.error("TaskGraphScheduler: {}", error_msg)
                break

            # Run ready nodes concurrently
            async def _run_node(node: TaskNode) -> Tuple[str, bool, Any]:
                logger.info("TaskGraphScheduler: Running node '{}' [{}] on agent '{}'", node.title, node.id, node.target_agent)
                self.board.claim_task(node.id, node.target_agent)

                node.status = "running"
                try:
                    res = self.hive.send_message(
                        agent_id=node.target_agent,
                        message=node.payload or node.action,
                        sender="task_scheduler",
                    )
                    success = not str(res).startswith("Error:")
                    return node.id, success, res
                except Exception as e:
                    logger.error("Node execution error: {}", e)
                    return node.id, False, str(e)
                finally:
                    self.board.release_task(node.id, node.target_agent)

            tasks = [_run_node(node) for node in ready_nodes]
            batch_results = await asyncio.gather(*tasks)

            for node_id, success, res in batch_results:
                node = remaining_nodes.pop(node_id)
                node_results[node_id] = res

                if success:
                    node.status = "completed"
                    completed_node_ids.add(node_id)
                    self.board.post(
                        topic=f"workflow:{graph.id}",
                        content={"node_id": node_id, "title": node.title, "status": "completed", "result": str(res)[:100]},
                        author=node.target_agent,
                    )
                else:
                    node.status = "failed"
                    failed_node_ids.add(node_id)
                    self.board.post(
                        topic=f"workflow:{graph.id}",
                        content={"node_id": node_id, "title": node.title, "status": "failed", "error": str(res)},
                        author=node.target_agent,
                    )

        duration = round(time.time() - start_time, 2)
        overall_success = len(failed_node_ids) == 0 and len(completed_node_ids) == len(graph.nodes)

        event_log.log_event(
            "workflow_finished",
            source="task_scheduler",
            data={
                "plan_id": graph.id,
                "success": overall_success,
                "completed": len(completed_node_ids),
                "failed": len(failed_node_ids),
                "duration_s": duration,
            },
        )

        return WorkflowExecutionResult(
            plan_id=graph.id,
            goal=graph.goal,
            success=overall_success,
            duration_s=duration,
            nodes_completed=len(completed_node_ids),
            nodes_failed=len(failed_node_ids),
            node_results=node_results,
            error=None if overall_success else f"{len(failed_node_ids)} tasks failed",
        )


task_scheduler = TaskGraphScheduler()

__all__ = ["WorkflowExecutionResult", "TaskGraphScheduler", "task_scheduler"]
