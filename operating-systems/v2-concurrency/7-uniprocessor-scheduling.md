# Uniprocessor Scheduling

## Preface: Performance Terminalogy

| Key Word | Description |
| - | - |
| **Task/Job** | A unit of work that can be scheduled. |
| **Response time/delay** | The user-perceived time to do some task. |
| **Throughput** | The number of tasks completed per unit time. |
| **Predictability** | Inversely related to variance in response time for repeated tasks. |
| **Scheduling Overhead** | The time to switch between tasks. |
| **Fairness** | Equality in the number and timelines of resource allocations. |
| **Starvation** | Lack of progress for one task due to resources being allocated to higher-priority tasks. |
| **Workload** | The set of tasks to be scheduled. |

## Uniprocessor Scheduling

### First in, First Out (FIFO)

Complete tasks as they arrive, finishing one before starting the next. On a uni-processor system with a completely CPU bound workload, this is one of the best scheduling algorithm in terms of throughput since overhead is minimized. However, it is not good for interactive systems, since short tasks are delayed by long ones. Concretely, the average response time for a FIFO scheduler is in many cases much worse than for other scheduling algorithms.

**Memcached** from Facebook uses a FIFO scheduler to handle requests to the caches in front of their databases. This works because the requests are all in memory (CPU bound) and of roughly equal length. The simplicity of FIFO makes it a good choice for extremely high-throughput systems that can work under this consistent request pattern.

### Shortest Job First (SJF)

Complete the task with the shortest remaining time first. This is optimal in terms of average response time for a given set of tasks, but it is not implementable in practice because the run time of a task is not known in advance.

#### Bias Towards Short Tasks
SJF biases the scheduler towards short tasks, which can lead to starvation of long tasks. There is a fundamental tradeoff between average response time and the variance of response times. This is a problem in interactive systems, where long tasks are often user-initiated. Furthermore, this property can be taken advantage of by breaking a long task into many short tasks, and can even become a security vulnerability whereby malicious users can starve other users by submitting many short tasks.

#### Sample Bias
When evaluating the effectiveness of SJF compared to other scheduling algorithms, it is important to avoid sample bias. Starvation can occur for long tasks if there are always short tasks in the queue, and if you only sample response time for completed tasks, you will not see the starvation.

#### Bandwidth Constrained Web Services

SJF is in some ways ideal for a web services that is limited by its network egress bandwidth. In this case, the shortest jobs are the ones that can be sent out the door the fastest, and the system can be optimized for throughput by minimizing the time it takes to send out the most data. Since response times would be limited by the network for larger requests anyways, optimizing for the shortest jobs is a good strategy.

If a server becomes overloaded, it can start dropping larger requests. This is a natural form of load shedding, and requires additional logic to handle the dropped requests.

### Round Robin (RR)

Each task in a queue is run for a fixed **time quantum**. If it is not finished, the process is preempted by a timer interrupt and put at the end of the queue. This makes it impossible for a task to starve indefinitely. The time quantum should be chosen to be long enough to minimize the overhead of context switching, but short enough to ensure good response time.

#### Overhead of RR Context Switching

There is a tradeoff between responsiveness and overhead, mainly due to the invalidation of cache entries between context switches. It is not nessesarily possible to maintain a good cache hit rate with a very short time quantum, since the cache will be invalidated every time a new task is run. Increasing the time quantum doesn't reduce the overhead of context switching, but it does reduce the frequency of context switches, thus improving the cache hit rate.

You can view RR as a compromise between FIFO and SJF. RR with an infinite time quantum is equivalent to FIFO. A special case of SJF can be thought of as having a "time quantum" of a single instruction with 0 overhead. Then, tasks would finish in the order of their lengths, albeit with alonger response times for shorter tasks than SJF without a time quantum.

**Simultaneous Multithreading (SMT)** is a technology that allows multiple threads to issue instructions to a superscalar processor in the same cycle. This can be thought of as a form of hardware-level round-robin scheduling without the overhead of context switching.

#### Maximizing Response Delay

Consider a workload of $n$ tasks, each of which take $t \cdot q$ seconds to complete ($q$ being the time quantum).

Assuming no scheduling overhead, the overall throughput of RR, SJF, and FIFO are all equal ($n \cdot t \cdot q$). However, the average response time for RR is much worse than SJF and FIFO (derivation below).

With RR, all tasks will complete during the last round of scheduling. With our parameters, this round begins at time $(n \cdot q) \cdot (t - 1)$, so our average response time is:

$$
T_{\text{RR}} = \frac{1}{n} \sum_{i=1}^{n} (nq)(t - 1) + iq
$$

$$
= q\frac{(n + 1) (2t - 1)}{2}
$$

SJF and FIFO behave identically in this case, and have an average repsonse time as follows:

$$
T_{\text{SJF}} = T_{\text{FIFO}} = \frac{1}{n} \sum_{i=1}^{n} iqt =  q\frac{(n + 1)t}{2}
$$

This illustrates that RR has a much worse average response time than SJF and FIFO, but the same throughput. Generally, if **response time** is the most important metric, round-robin is not the best choice.

#### Silver Lining: Stream Processing

Round-robin scheduling is ideal for applications where the tasks are not discrete workload on the client side, but rather a continuous stream of data. For instance, when streaming video from a server, the server can send out a small chunk of video to each client in a round-robin fashion. This is a good way to ensure that all clients are served equally, and that no client is starved.

#### Mixed Workloads Being Bad for RR

Systems that need to schedule a mixture of I/O and CPU-bound tasks can have a hard time with RR. For instance, a text editor program needs to minimize the latency of user input being displayed on screen. If the text editor is running in a round-robin system, it would likely need to wait for the next round of scheduling to display the user's input.

Consider another case where a naive browser is connected to a slow link and needs to download a large file in the background, all while the user continues to surf the web. If network I/O is scheduled in a round-robin fashion, the user's web browsing experience will be degraded.

### Max Min Fairness

Max Min Fairness is a scheduling algorithm that tries to minimize the maximum response time of any task, effectively minimizing the variance.

If all processes are compute-bound, then the algorithm is equivalent to RR. However, I/O bound processes that don't use their full time quantum will be allowed to execute fully, and then their remaining allocation will be equally distributed to the other tasks. This pattern continues until all CPU time is used up.

A theoretical implementation would be to always schedule the task that has used the processor for the least amount of time. This doesn't work in practice because two equally short tasks will starve each other.

Instead, the algorithm can be approximated by tracking CPU usage time only by the quantum, and allowing tasks to get no more than 1 extra quantum of CPU time than their ideal max min allocation. This however still requires a priority queue to be maintained, and is not practical for commercial operating systems.

### Multi-level Feedback Queue (MLFQ)

__*Grocery store lines with "express lanes" of multiple priorities*__

MLFQ attempts to find a compromise between the following goals:

| Goal | Description |
| - | - |
| **Responsiveness** | Short tasks should be completed quickly. |
| **Low Overhead** | Minimize the number of preemptions, as well as the time spent scheduling. |
| **Starvation Avoidance** | All tasks should be able to make progress. |
| **Background Tasks** | Deferrable tasks like system maintenance should not interfere with foreground tasks. |
| **Fairness** | Assign non-background tasks an approximately max-min fair share of the CPU. |


#### MLFQ Algorithm

Maintain multiple RR queues, each with a different priority and time quantum. Tasks with higher priority have smaller time quanta and preempt lower priority tasks. Tasks at the same level are scheduled RR.

Tasks are initially placed in the highest priority queue. If a task uses its entire time quantum, it is demoted to the next lower priority queue. If a task uses less than its entire time quantum, it is either kept in the same queue or moved up. This is a form of SJF within each queue.

To prevent starvation and achieve max-min fairness, the scheduler monitors process execution time on the CPU. The scheduler then only schedules processes that have yet to recieve their fair share. If a process already got its fair share of the CPU, it is demoted to a lower priority, and if they've yet to get their fair share, they are promoted to a higher priority.




