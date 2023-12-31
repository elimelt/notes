package Misc;
import java.util.Stack;

public class ReorderList {
    public void reorderList(ListNode head) {
        if (head == null || head.next == null)
            return;

        Stack<ListNode> s = new Stack<>();

        ListNode curr = head;

        while (curr !=  null) {
            s.push(curr);
            curr = curr.next;
        }

        int size = s.size();

        ListNode newHead = head, tail = newHead;
        curr = head.next;

        int currSize = 1;
        while (!s.isEmpty() && currSize < size) {
            tail.next = s.pop();
            tail = tail.next;
            currSize++;
            tail.next = curr;
            tail = tail.next;
            currSize++;
            curr = curr.next;
        }

        tail.next = null;
        head = newHead;

    }

    
 
    public class ListNode {
        int val;
        ListNode next;
        
        ListNode(int val) { this.val = val; }
        
        ListNode(int val, ListNode next) { 
            this.val = val; 
            this.next = next; 
        }
    }

}
