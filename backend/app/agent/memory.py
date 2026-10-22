
from __future__ import annotations

from pathlib import Path
from typing import Any

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


class SQLiteMemoryManager:
    """
    Quản lý hai loại bộ nhớ của AI Agent trên cùng một SQLite database:

    1. Short-term memory:
       LangGraph AsyncSqliteSaver lưu checkpoint theo thread_id.

    2. Long-term memory:
       Bảng agent_memories lưu thông tin được chọn để tái sử dụng.

    Vòng đời:
        manager = SQLiteMemoryManager(db_path)
        await manager.open()

        # Sử dụng manager.checkpointer và các hàm memory.

        await manager.close()
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._checkpoint_context: Any = None
        self._checkpointer: AsyncSqliteSaver | None = None
        self._opened = False

    # =========================================================
    # 1. KHỞI TẠO VÀ ĐÓNG TÀI NGUYÊN
    # =========================================================

    async def open(self) -> None:
        """Mở Checkpointer và khởi tạo bảng bộ nhớ dài hạn."""
        if self._opened:
            return

        self._checkpoint_context = AsyncSqliteSaver.from_conn_string(
            str(self.db_path)
        )

        try:
            self._checkpointer = (
                await self._checkpoint_context.__aenter__()
            )

            await self._initialize_long_term_memory()
            self._opened = True

        except Exception:
            self._checkpointer = None

            await self._checkpoint_context.__aexit__(
                *(__import__("sys").exc_info())
            )
            self._checkpoint_context = None
            raise

    async def close(self) -> None:
        """Đóng Checkpointer khi backend dừng."""
        if self._checkpoint_context is not None:
            context = self._checkpoint_context

            self._checkpoint_context = None
            self._checkpointer = None
            self._opened = False

            await context.__aexit__(None, None, None)

    @property
    def checkpointer(self) -> AsyncSqliteSaver:
        """Cung cấp Checkpointer cho LangGraph."""
        if not self._opened or self._checkpointer is None:
            raise RuntimeError(
                "SQLiteMemoryManager chưa được mở. "
                "Hãy gọi await manager.open() trước."
            )

        return self._checkpointer

    async def _initialize_long_term_memory(self) -> None:
        """Tạo bảng memory nếu chưa tồn tại."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")

            await db.execute("""
                CREATE TABLE IF NOT EXISTS agent_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL DEFAULT 'default',
                    memory_key TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'general',
                    created_at TEXT NOT NULL DEFAULT (
                        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                    ),
                    updated_at TEXT NOT NULL DEFAULT (
                        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                    ),
                    UNIQUE(user_id, memory_key)
                )
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_memories_category
                ON agent_memories(user_id, category)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_memories_updated
                ON agent_memories(user_id, updated_at)
            """)

            await db.commit()

    def _ensure_open(self) -> None:
        if not self._opened:
            raise RuntimeError(
                "SQLiteMemoryManager chưa được khởi tạo."
            )

    # =========================================================
    # 2. BỘ NHỚ DÀI HẠN: LƯU VÀ CẬP NHẬT
    # =========================================================

    async def save_memory(
        self,
        memory_key: str,
        content: str,
        category: str = "general",
        user_id: str = "default",
    ) -> None:
        """
        Lưu memory mới hoặc cập nhật memory đã tồn tại.

        Cùng user_id và memory_key: cập nhật nội dung.
        Khác user_id: lưu thành memory độc lập.
        """
        self._ensure_open()

        memory_key = memory_key.strip()
        content = content.strip()
        category = category.strip() or "general"
        user_id = user_id.strip()

        if not memory_key:
            raise ValueError("memory_key không được để trống.")

        if not content:
            raise ValueError("content không được để trống.")

        if not user_id:
            raise ValueError("user_id không được để trống.")

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO agent_memories (
                    user_id,
                    memory_key,
                    content,
                    category
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, memory_key)
                DO UPDATE SET
                    content = excluded.content,
                    category = excluded.category,
                    updated_at = strftime(
                        '%Y-%m-%dT%H:%M:%fZ', 'now'
                    )
            """, (user_id, memory_key, content, category))

            await db.commit()

    # =========================================================
    # 3. BỘ NHỚ DÀI HẠN: TÌM KIẾM
    # =========================================================

    async def search_memories(
        self,
        keyword: str,
        limit: int = 10,
        user_id: str = "default",
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Tìm memory theo từ khóa trong key hoặc content.

        Đây là tìm kiếm chuỗi LIKE, chưa phải semantic search.
        """
        self._ensure_open()

        keyword = keyword.strip()
        if not keyword:
            return []

        limit = max(1, min(int(limit), 100))
        pattern = f"%{keyword}%"

        query = """
            SELECT
                id,
                user_id,
                memory_key,
                content,
                category,
                created_at,
                updated_at
            FROM agent_memories
            WHERE user_id = ?
              AND (
                  memory_key LIKE ? ESCAPE '\\'
                  OR content LIKE ? ESCAPE '\\'
              )
        """
        params: list[Any] = [user_id, pattern, pattern]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()

        return [dict(row) for row in rows]

    # =========================================================
    # 4. BỘ NHỚ DÀI HẠN: LẤY DANH SÁCH
    # =========================================================

    async def list_memories(
        self,
        user_id: str = "default",
        category: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Liệt kê các memory của người dùng."""
        self._ensure_open()

        limit = max(1, min(int(limit), 100))

        query = """
            SELECT
                id,
                user_id,
                memory_key,
                content,
                category,
                created_at,
                updated_at
            FROM agent_memories
            WHERE user_id = ?
        """
        params: list[Any] = [user_id]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()

        return [dict(row) for row in rows]

    # =========================================================
    # 5. BỘ NHỚ DÀI HẠN: XÓA
    # =========================================================

    async def delete_memory(
        self,
        memory_key: str,
        user_id: str = "default",
    ) -> bool:
        """Xóa một memory theo khóa và người sở hữu."""
        self._ensure_open()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                DELETE FROM agent_memories
                WHERE user_id = ? AND memory_key = ?
            """, (user_id, memory_key))

            await db.commit()
            deleted = cursor.rowcount > 0
            await cursor.close()

        return deleted

    # =========================================================
    # 5. HỘI THOẠI: DANH SÁCH THREAD VÀ LỊCH SỬ
    # =========================================================

    @staticmethod
    def _message_to_dict(message: Any) -> dict[str, str] | None:
        """Chuẩn hóa LangChain message thành dữ liệu frontend cần."""
        message_type = getattr(message, "type", None)
        content = getattr(message, "content", "")

        if message_type not in {"human", "ai"}:
            return None

        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    parts.append(block["text"])
            text = "\n".join(parts)
        else:
            text = str(content or "")

        if not text.strip():
            return None

        return {
            "role": "user" if message_type == "human" else "ai",
            "text": text,
        }

    async def list_threads(
        self,
        user_id: str = "default",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Lấy danh sách cuộc trò chuyện từ LangGraph checkpoints."""
        self._ensure_open()
        user_id = user_id.strip() or "default"
        limit = max(1, min(int(limit), 100))

        threads: dict[str, dict[str, Any]] = {}

        # Checkpoint được trả theo thứ tự mới -> cũ. Vì vậy checkpoint đầu tiên
        # gặp của mỗi thread chính là snapshot mới nhất của thread đó.
        async for item in self.checkpointer.alist(
            None,
            filter={"user_id": user_id},
            limit=None,
        ):
            thread_id = item.config["configurable"]["thread_id"]
            if thread_id in threads:
                continue

            checkpoint = item.checkpoint
            messages = checkpoint.get("channel_values", {}).get("messages", [])
            normalized = [
                converted
                for message in messages
                if (converted := self._message_to_dict(message)) is not None
            ]

            if not normalized:
                continue

            first_user = next(
                (m["text"] for m in normalized if m["role"] == "user"),
                "Cuộc trò chuyện mới",
            )

            threads[thread_id] = {
                "thread_id": thread_id,
                "title": first_user.strip().replace("\n", " ")[:80],
                "preview": normalized[-1]["text"].strip().replace("\n", " ")[:120],
                "message_count": len(normalized),
                "updated_at": checkpoint.get("ts"),
            }

            if len(threads) >= limit:
                break

        return list(threads.values())

    async def get_thread_messages(
        self,
        thread_id: str,
        user_id: str = "default",
    ) -> list[dict[str, str]]:
        """Lấy toàn bộ message của checkpoint mới nhất của một thread."""
        self._ensure_open()
        thread_id = thread_id.strip()
        user_id = user_id.strip() or "default"

        if not thread_id:
            return []

        item = await self.checkpointer.aget_tuple(
            {"configurable": {"thread_id": thread_id}}
        )
        if item is None:
            return []

        metadata_user_id = (
            item.metadata.get("user_id")
            or (item.config.get("configurable") or {}).get("user_id")
            or "default"
        )
        if metadata_user_id != user_id and user_id != "default":
            return []

        messages = item.checkpoint.get("channel_values", {}).get("messages", [])
        return [
            converted
            for message in messages
            if (converted := self._message_to_dict(message)) is not None
        ]
