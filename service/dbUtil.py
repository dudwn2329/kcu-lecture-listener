import sqlite3

DB_FILE = "my_database.db"


class DbUtil:
    def __init__(self):

        self.conn = sqlite3.connect(DB_FILE)

    def getCursor(self):
        cur = self.conn.cursor()
        return cur

    def exec(self, query, returnId=False, params=None):
        try:
            cur = self.getCursor()
            if params is not None:
                cur.execute(query, params)
            else:
                cur.execute(query)
        except:
            # 오류 발생 시 connection 재연결
            self.conn = sqlite3.connect(DB_FILE)
            cur = self.getCursor()
            if params is not None:
                cur.execute(query, params)
            else:
                cur.execute(query)
        result = cur.fetchall()
        if returnId:
            # insert 후 id가 필요할 때 사용
            return cur.lastrowid
        cur.close()
        self.conn.commit()
        return result

    def getRows(self, query, params=None):
        cursor = self.getCursor()
        if params is not None:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        rows = cursor.fetchall()
        return rows

    def close(self):
        self.conn.close()
