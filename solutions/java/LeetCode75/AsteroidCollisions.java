package LeetCode75;

import java.util.Stack;

public class AsteroidCollisions {
    public int[] asteroidCollision(int[] asteroids) {
        Stack<Integer> r = new Stack<>();

        for (int curr : asteroids) {
            if (curr > 0 || (curr < 0 && (r.isEmpty() || r.peek() < 0)))
                r.push(curr);
            else {
                while (Math.abs(r.peek()) < Math.abs(curr)) {
                    r.pop();
                    if (r.isEmpty() || r.peek() < 0) {
                        r.push(curr);
                        break;
                    }
                }

                if (Math.abs(r.peek()) == Math.abs(curr) && r.peek() > curr)
                    r.pop();
            }

        }
        int[] res = new int[r.size()];
        for (int i = res.length - 1; i >= 0; i--)
            res[i] = r.pop();
        return res;
    }
}
