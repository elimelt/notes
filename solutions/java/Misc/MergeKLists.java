package Misc;

import java.util.PriorityQueue;
import Misc.ReorderList.ListNode;

public class MergeKLists {
    public ListNode mergeKLists(ListNode[] lists) {
        if (lists.length == 0)
            return null;

        PriorityQueue<ListNode> pq = new PriorityQueue<>((a, b) -> a.val - b.val);

        for (ListNode l : lists)
            if (l != null) pq.add(l);

        ListNode head = null, curr = null;

        while(!pq.isEmpty()) {
            if (head == null) {
                head = pq.remove();
                curr = head;
                if (head.next != null)
                    pq.add(head.next);
                continue;
            }

            curr.next = pq.remove();

            curr = curr.next;

            if (curr.next != null)
                pq.add(curr.next);
        }

        if (curr != null)
            curr.next = null;

        return head;

    }
}
