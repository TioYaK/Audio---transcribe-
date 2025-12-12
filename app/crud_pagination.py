# Adicionar ao final do arquivo crud.py

    def get_user_tasks_paginated(self, owner_id: str, offset: int, limit: int, include_text: bool = False):
        """Get user's tasks with pagination"""
        tasks = self.db.query(models.TranscriptionTask).filter(
            models.TranscriptionTask.owner_id == owner_id,
            models.TranscriptionTask.status.in_(["completed", "failed"])
        ).order_by(
            models.TranscriptionTask.completed_at.desc()
        ).offset(offset).limit(limit).all()
        
        return [task.to_dict(include_text=include_text) for task in tasks]
    
    def get_all_tasks_admin_paginated(self, offset: int, limit: int, include_text: bool = False):
        """Get all tasks with pagination (admin only)"""
        results = (
            self.db.query(models.TranscriptionTask, models.User.full_name, models.User.username)
            .outerjoin(models.User, models.TranscriptionTask.owner_id == models.User.id)
            .order_by(models.TranscriptionTask.completed_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        tasks_data = []
        for task, full_name, username in results:
            t_dict = task.to_dict(include_text=include_text)
            t_dict["owner_name"] = full_name or username or "Desconhecido"
            tasks_data.append(t_dict)
        return tasks_data
    
    def count_all_tasks(self):
        """Count all tasks"""
        return self.db.query(models.TranscriptionTask).count()
    
    def count_user_completed_tasks(self, owner_id: str):
        """Count user's completed/failed tasks"""
        return self.db.query(models.TranscriptionTask).filter(
            models.TranscriptionTask.owner_id == owner_id,
            models.TranscriptionTask.status.in_(["completed", "failed"])
        ).count()
