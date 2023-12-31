package LeetCode75;

import java.util.LinkedList;
import java.util.Queue;

public class NearestExit {
    public int nearestExit(char[][] maze, int[] entrance) {
        int m = maze.length, n = maze[0].length;
        
        boolean[][] visited = new boolean[m][n];
        for (int r = 0; r < m; r++)
            for (int c = 0; c < n; c++)
                visited[r][c] = (maze[r][c] == '+') ? true : false;

        Queue<Pair> q = new LinkedList<>();
        q.add(new Pair(entrance[0], entrance[1]));

        int moves = 0;

        while (!q.isEmpty()) {
            int size = q.size();
            for (int i = 0; i < size; i++) {
                Pair curr = q.remove();
                if (visited[curr.row][curr.col])
                    continue;

                visited[curr.row][curr.col] = true;

                if ( isExit(m, n, curr) && 
                    (curr.row != entrance[0] || curr.col != entrance[1])
                ) return moves;

                for (Pair adj : curr.getSurrounding()) 
                    if (isInMaze(m, n, adj) && !visited[adj.row][adj.col]) 
                        q.add(adj);
            }
            moves++;
        }

        return -1;
    }

    private boolean isInMaze(int m, int n, Pair p) {
        return p.row < m && 
            p.col < n && 
            p.row >= 0 && 
            p.col >= 0;
    }

    private boolean isExit(int m, int n, Pair p) {
        return p.row == m - 1 || 
            p.col == n - 1 || 
            p.row == 0 || 
            p.col == 0;
    }
    
    private class Pair {
        public int row, col;

        public Pair(int r, int c) {
            this.row = r;
            this.col = c;
        }

        public String toString() {
            return "row: " + this.row + ", col: " + this.col;
        }

        public Pair[] getSurrounding() {
            return new Pair[]{
                new Pair(this.row + 1, this.col),
                new Pair(this.row - 1, this.col),
                new Pair(this.row, this.col + 1),
                new Pair(this.row, this.col - 1)
            };
        }
    }
}
