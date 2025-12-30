package Misc;

import Misc.ReorderList.ListNode;

public class RotateList {
    public ListNode rotateRight(ListNode head, int k) {
        if (k == 0 || head == null || head.next == null)
            return head;

        ListNode curr = head, newTail = head;
        int size = 0;
        while (curr != null) {
            curr = curr.next;
            size++;
        }

        k %= size;

        if (k == 0)
            return head;

        curr = head;

        for (int i = 0; i < k; i++)
            curr = curr.next;

        while (curr.next != null) {
            curr = curr.next;
            newTail = newTail.next;
        }

        ListNode newHead = newTail.next;
        newTail.next = null;
        curr.next = head;
        return newHead;
    }
}
