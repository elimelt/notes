package Misc;

/* https://leetcode.com/problems/sort-list */

import java.util.Arrays;
import Misc.ReorderList.ListNode;

public class SortList {
    public ListNode sortList(ListNode head) {
        if (head == null || head.next == null)
            return head;

        ListNode curr = head;
        int size = 0;
        while (curr != null) {
            curr = curr.next;
            size++;
        }

        ListNode[] nodes = new ListNode[size];

        curr = head;

        for (int i = 0; i < size; i++) {
            nodes[i] = curr;
            curr = curr.next;
        }

        Arrays.sort(nodes, (n1, n2) -> n1.val - n2.val);

        ListNode newHead = nodes[0];

        curr = newHead;

        for (int i = 1; i < size; i++) {
            curr.next = nodes[i];
            curr = curr.next;
        }

        curr.next = null;
        return newHead;
    }
    
}
