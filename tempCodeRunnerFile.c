#include <stdio.h>

int main()
{
    int n, i, j;
    int process[20];
    int arrivalTime[20], burstTime[20];
    int waitingTime[20], turnaroundTime[20], completionTime[20];
    int temp;
    float avgWaitingTime = 0, avgTurnaroundTime = 0;
    printf("           CPU SCHEDULING - FCFS            \n");
    printf("Name            : Vanshika Ghatwal\n");
    printf("Enrollment No.  : 03525502724\n");
    printf("Enter the number of processes: ");
    scanf("%d", &n);
    printf("\nEnter Arrival Time and Burst Time for each process:\n");
    for (i = 0; i < n; i++)
    {
        process[i] = i + 1;
        printf("\nProcess P%d\n", i + 1);
        printf("Arrival Time: ");
        scanf("%d", &arrivalTime[i]);
        printf("Burst Time: ");
        scanf("%d", &burstTime[i]);
    }
    for (i = 0; i < n - 1; i++)
    {
        for (j = i + 1; j < n; j++)
        {
            if (arrivalTime[i] > arrivalTime[j])
            {
                temp = arrivalTime[i];
                arrivalTime[i] = arrivalTime[j];
                arrivalTime[j] = temp;
                temp = burstTime[i];
                burstTime[i] = burstTime[j];
                burstTime[j] = temp;
                temp = process[i];
                process[i] = process[j];
                process[j] = temp;
            }
        }
    }
    completionTime[0] = arrivalTime[0] + burstTime[0];
    for (i = 1; i < n; i++)
    {
        if (completionTime[i - 1] < arrivalTime[i])
        {
            completionTime[i] = arrivalTime[i] + burstTime[i];
        }
        else
        {
            completionTime[i] = completionTime[i - 1] + burstTime[i];
        }
    }
    for (i = 0; i < n; i++)
    {
        turnaroundTime[i] = completionTime[i] - arrivalTime[i];
        waitingTime[i] = turnaroundTime[i] - burstTime[i];
        avgWaitingTime += waitingTime[i];
        avgTurnaroundTime += turnaroundTime[i];
    }
    avgWaitingTime = avgWaitingTime / n;
    avgTurnaroundTime = avgTurnaroundTime / n;
    printf("           FCFS SCHEDULING RESULT           \n");
    printf("\nProcess\t\tArrival\t\tBurst\tCompletion\tWaiting\tTurnaround\n");
    for (i = 0; i < n; i++)
    {
        printf("P%d\t\t\t\t%d\t\t\t%d\t\t%d\t\t\t%d\t\t%d\n",
               process[i],
               arrivalTime[i],
               burstTime[i],
               completionTime[i],
               waitingTime[i],
               turnaroundTime[i]);
    }
    printf("\nAverage Waiting Time    = %.2f", avgWaitingTime);
    printf("\nAverage Turnaround Time = %.2f\n", avgTurnaroundTime);
    return 0;
}
