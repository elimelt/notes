package LeetCode75;

import java.util.Arrays;
import java.util.PriorityQueue;

/* https://leetcode.com/problems/total-cost-to-hire-k-workers */

public class CostToHireKWorkers {
    public long totalCost(int[] costs, int k, int candidates) {
        PriorityQueue<Pair> pq = new PriorityQueue<>((a, b) -> a.compare(b));
        boolean[] visited = new boolean[costs.length];
        Arrays.fill(visited, false);

        int lo = 0, hi = costs.length - 1, count = 0;
        long total = 0;

        while (lo < candidates) {
            if (pq.size() == costs.length) break;
            if (hi == lo) {
                visited[hi] = true;
                pq.add(new Pair(hi, costs[hi]));
                break;    
            }
            visited[lo] = !visited[lo];
            visited[hi] = !visited[hi];
            pq.add(new Pair(lo, costs[lo++]));
            pq.add(new Pair(hi, costs[hi--]));
        }

        // all elements are candidates
        if (visited[lo]) {
            for (; count < k; count++) total += pq.remove().c; 
            return total;
        }

        while (count++ < k) {
            Pair next = pq.remove();
            total += next.c;
            if (visited[lo] || visited[hi]) {
                continue;
            }

            if (next.i <= lo) {
                visited[lo] = true;
                pq.add(new Pair(lo, costs[lo]));
                lo++;
            } else if (next.i > hi) {
                visited[hi] = true;
                pq.add(new Pair(hi, costs[hi]));
                hi--;
            }
        }
        return total;
        
    }

    public class Pair {
        int i, c;
        public Pair(int index, int cost) { i = index; c = cost; }

        public int compare(Pair other) { 
            return this.c != other.c
                ? this.c - other.c 
                : this.i - other.i; 
        }

        public String toString() { return "(" + this.i + ", " + this.c + ")"; }
    }
}
