import openpyxl
import numpy as np
import os
import time
from docplex.mp.model import Model

class Task():
    def __init__(self, id, duration, power):
        self.id = id
        self.duration = duration
        self.power = power
    
    def __init__(self, id, duration, power, workstation, start_at):
        self.id = id
        self.duration = duration
        self.power = power
        self.workstation = workstation
        self.start_at = start_at
    
    def setId(self, id):
        self.id = id
    
    def getId(self):
        return self.id
    
    def setDuration(self, duration):
        self.duration = duration
    
    def getDuration(self):
        return self.duration
    
    def setPower(self, power):
        self.power = power
    
    def getPower(self):
        return self.power
    
    def setWorkstation(self, workstation):
        self.workstation = workstation
    
    def getWorkstation(self):
        return self.workstation
    
    def setStartAt(self, start_at):
        self.start_at = start_at
    
    def getStartAt(self):
        return self.start_at

def generatePowerConsumption(file_name, file_path, n):
    file = open(file_path, 'a')
    for j in range(1, n + 1):
        file.write(str(np.random.randint(5, 51)) + '\n')
    file.close()
    return

def readDatasetFile(dataset_number):
    excelFile = openpyxl.load_workbook('./datasets/dataset.xlsx').active
    row = excelFile[dataset_number]
    file_name = str(row[0].value).upper()
    global n, m, c, task_time, precedence_constraints, task_power
    m = int(row[1].value)
    c = int(row[2].value)

    in2File = open('./datasets/precedence_graphs/' + file_name + '.IN2', 'r')
    content = in2File.readlines()
    for index, line in enumerate(content):
        line = line.strip()
        if index == 0:
            n = int(line)
        elif index in range(1, n + 1):
            task_time.append(int(line))
        else:
            constraints = tuple(map(int, line.split(',')))  # Chuyển thành tuple số nguyên
            if constraints != (-1, -1):  # Bỏ qua (-1, -1)
                precedence_constraints.append(constraints)
            else:
                break
    in2File.close()

    txtFilePath = './datasets/task_power/' + file_name + '.txt'
    if os.path.isfile(txtFilePath):
        txtFile = open(txtFilePath, 'r')
        power_content = txtFile.readlines()
        for index, line in enumerate(power_content):
            line = line.strip()
            task_power.append(int(line))
        txtFile.close()
    else:
        generatePowerConsumption(file_name, txtFilePath, n)
        txtFile = open(txtFilePath, 'r')
        power_content = txtFile.readlines()
        for index, line in enumerate(power_content):
            line = line.strip()
            task_power.append(int(line))
        txtFile.close()

    print('[file_name]', file_name)
    print('[n]', n)
    print('[m]', m)
    print('[c]', c)

def printAssumption(model):
    print('\n')
    print(f"[#Vars] {model.number_of_variables}")
    print(f"[#Cons] {model.number_of_constraints}")

def printResult(W_max, model, X, S, time_execution):
    print('\n')
    # print('[Peak]', best_value)
    # print('[#Sol]', len(solutions))
    # print('[#SolBB]', best_iteration)
    # print('[Time]', round(time_execution, 3), 's')
    # Count variables and constraints
    print(f"[W_max] {W_max.solution_value}")
    print(f'[Time] {round(time_execution, 3)} s')

    tasks = []
    for j in range(1, n + 1):
        for k in range(1, m + 1):
            for t in range(0, c - 1 + 1):
                if X[j, k].solution_value > 0.5 and S[j, t].solution_value > 0.5:
                    tasks.append(Task(j, task_time[j], task_power[j], k, t))
                    break
    for task in tasks:
        if isinstance(task, Task):
            print('task', task.getId(), ': duration=', task.getDuration(), 'power=', task.getPower(), 'workstation=', task.getWorkstation(), 'start at=', task.getStartAt())
    print('\n')
    # print('[best_solution]')
    # printSolution(best_solution, best_iteration, best_power_consumption, best_value)

def generateConstraints(n, m, c, task_time, precedence_constraints, model, X, S, W_max):
    # (1) Hàm mục tiêu: Minimize Wmax
    model.minimize(W_max)

    # (2) Mỗi task phải được gán cho đúng một workstation
    for j in range(1, n + 1):
        model.add_constraint(model.sum(X[j, k] for k in range(1, m + 1)) == 1)

    # (3) Tổng thời gian xử lý của các task tại một workstation không vượt quá thời gian chu kỳ
    for k in range(1, m + 1):
        model.add_constraint(model.sum(task_time[j] * X[j, k] for j in range(1, n + 1)) <= c)

    # (4) Ràng buộc thứ tự thực hiện giữa các task
    for (i, j) in precedence_constraints:
        for k in range(1, m + 1):
            model.add_constraint(X[j, k] <= model.sum(X[i, h] for h in range(1, k + 1)))

    # (5) Mỗi task phải bắt đầu tại đúng một thời điểm
    for j in range(1, n + 1):
        model.add_constraint(model.sum(S[j, t] for t in range(0, c - task_time[j] + 1)) == 1)

    # (6) Nếu task i trước task j và cùng trạm, thì i phải bắt đầu trước j
    for (i, j) in precedence_constraints:
        for k in range(1, m + 1):
            for t in range(0, c - task_time[j] + 1):
                model.add_constraint(S[j, t] <= model.sum(S[i, T] for T in range(0, t - task_time[i] + 1)) + 2 - X[i, k] - X[j, k])

    # (7) Không thể có hai task chạy đồng thời tại cùng một workstation
    for i in range(1, n):
        for j in range(i + 1, n + 1):
            for k in range(1, m + 1):
                for t in range(0, c - 1 + 1):
                    model.add_constraint(X[i, k] + X[j, k] + model.sum(S[i, T] for T in range(max(t - task_time[i] + 1, 0), t + 1)) + model.sum(S[j, T] for T in range(max(t - task_time[j] + 1, 0), t + 1)) <= 3)

    # (8) Mức tiêu thụ năng lượng tại mỗi thời điểm không vượt quá Wmax
    for t in range(0, c - 1 + 1):
        model.add_constraint(model.sum(task_power[j] * model.sum(S[j, T] for T in range(max(t - task_time[j] + 1, 0), t + 1)) for j in range(1, n + 1)) <= W_max)

def ILPSolver(model):
    model.set_time_limit(3600)
    return model.solve(log_output = False)

# Global variables

# Variable read from file
n = 0 # number of tasks
m = 0 # number of workstations
c = 0 # cycle time

task_time = [None]
precedence_constraints = []
task_power = [None]

# n = 4 # number of tasks
# m = 3 # number of workstations
# c = 5 # cycle time

# task_time = [None, 5, 2, 3, 3]
# precedence_constraints = [(1, 2), (2, 3), (3, 4)]
# task_power = [None, 4, 4, 2, 4]

def main():
    global n, m, c, task_time, precedence_constraints, task_power, solution
    
    print('Type your dataset number: ')
    dataset_number = input()

    readDatasetFile(dataset_number)
    # print('[n]', n)
    # print('[m]', m)
    # print('[c]', c)
    # print('[task_time]', task_time)
    # print('[precedence_constraints]', precedence_constraints)
    # print('[task_power]', task_power)
    # print('\n')

    # Khởi tạo mô hình
    model = Model("SALB3PM")
    
    # Biến quyết định
    X = model.binary_var_dict(((j, k) for j in range(1, n + 1) for k in range(1, m + 1)), name="X")
    S = model.binary_var_dict(((j, t) for j in range(1, n + 1) for t in range(0, c - 1 + 1)), name="S")
    W_max = model.integer_var(name="W_max")
    # print('[X]', X)
    # print('[S]', S)
    # print('[W_max]', W_max)

    start = time.time()

    # preConstraints(n, m, c, task_time, precedence_constraints)
    generateConstraints(n, m, c, task_time, precedence_constraints, model, X, S, W_max)
    printAssumption(model)

    solution = ILPSolver(model)
    end = time.time()
    if not solution:
        print('No solution')
        return
    
    time_execution = end - start
    if time_execution > 3600:
        print('time out')
    printResult(W_max, model, X, S, time_execution)

main()