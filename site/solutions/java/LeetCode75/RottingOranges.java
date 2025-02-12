package LeetCode75;

import java.util.LinkedList;
import java.util.Queue;

public class RottingOranges {
    public int orangesRotting(int[][] grid) {
        int m = grid.length, n = grid[0].length, count = 0;
        Queue<Pair> q = new LinkedList<>();

        for (int i = 0; i < m; i++) {
            for (int j = 0; j < n; j++) {
                if (grid[i][j] == 1)
                    count++;
                if (grid[i][j] == 2)
                    q.add(new Pair(i, j, 0));
            }
        }

        int time = 0;
        while (!q.isEmpty()) {
            Pair curr = q.remove();
            time = curr.t;

            if (curr.i > 0 && grid[curr.i - 1][curr.j] == 1) {
                grid[curr.i - 1][curr.j] = 2;
                q.add(new Pair(curr.i - 1, curr.j, curr.t + 1));
                count--;
            }

            if (curr.i < m - 1 && grid[curr.i + 1][curr.j] == 1) {
                grid[curr.i + 1][curr.j] = 2;
                q.add(new Pair(curr.i + 1, curr.j, curr.t + 1));
                count--;
            }

            if (curr.j > 0 && grid[curr.i][curr.j - 1] == 1) {
                grid[curr.i][curr.j - 1] = 2;
                q.add(new Pair(curr.i, curr.j - 1, curr.t + 1));
                count--;
            }

            if (curr.j < n - 1 && grid[curr.i][curr.j + 1] == 1) {
                grid[curr.i][curr.j + 1] = 2;
                q.add(new Pair(curr.i, curr.j + 1, curr.t + 1));
                count--;
            }
        }

        return count == 0 ? time : -1;

    }

    private class Pair {
        public int i, j, t;

        public Pair(int i, int j, int t) {
            this.i = i;
            this.j = j;
            this.t = t;
        }
    }
}
