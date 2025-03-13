Конструктор предобработки данных
Описание
Конструктор предобработки данных - это веб-приложение, предназначенное для автоматизации процесса подготовки данных перед построением прогнозных моделей. Приложение поддерживает работу как с табличными данными, так и с временными рядами, предоставляя интуитивный интерфейс для различных методов трансформации данных.
Ключевые возможности

Загрузка и анализ данных в форматах CSV и Excel
Автоматическое определение типов данных и рекомендация подходящих методов предобработки
Визуализация и предпросмотр результатов обработки
Экспорт обработанных данных для дальнейшего использования
Сохранение и повторное применение параметров масштабирования

Поддерживаемые методы предобработки

Общие методы:

Обработка пропущенных значений (заполнение средним, медианой, модой или удаление строк)
Обработка выбросов (методы Z-оценки и межквартильного размаха)
Стандартизация числовых данных (StandardScaler, MinMaxScaler)
Кодирование категориальных переменных (One-Hot, Label кодирование)
Снижение размерности (PCA)


Методы для временных рядов:

Лагирование переменных (создание признаков на основе предыдущих значений)
Скользящие статистики (среднее, стандартное отклонение, минимум, максимум)
Извлечение компонентов даты (год, месяц, квартал, день недели и т.д.)
Обратное масштабирование (для интерпретации результатов в исходном масштабе)



Запуск приложения
Запуск в Docker
Приложение контейнеризировано с использованием Docker, что упрощает его развертывание на различных платформах.
Windows

1. Установите Docker Desktop для Windows
2. Клонируйте репозиторий:
git clone https://github.com/yourusername/data-preprocessing-constructor.git
cd data-preprocessing-constructor 

3. Запустите контейнеры:
docker-compose up -d

4. Приложение будет доступно по адресу: http://localhost:8080
macOS

Установите Docker Desktop для Mac
Клонируйте репозиторий:
git clone https://github.com/yourusername/data-preprocessing-constructor.git
cd data-preprocessing-constructor
4. Запустите контейнеры:
docker-compose up -d
5. Приложение будет доступно по адресу: http://localhost:8080

Linux

1. Установите Docker и Docker Compose:
sudo apt-get update
sudo apt-get install docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker
2. Клонируйте репозиторий:
git clone https://github.com/yourusername/data-preprocessing-constructor.git
cd data-preprocessing-constructor
3. Запустите контейнеры:
sudo docker-compose up -d
4. Приложение будет доступно по адресу: http://localhost:8080

Запуск в Kubernetes
Для развертывания приложения в Kubernetes кластере вам потребуется подготовить следующие манифесты:

1. Создайте файл deployment.yaml:

apiVersion: apps/v1
kind: Deployment
metadata:
  name: data-preprocessing-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: data-preprocessing
  template:
    metadata:
      labels:
        app: data-preprocessing
    spec:
      containers:
      - name: data-preprocessing
        image: yourusername/data-preprocessing-constructor:latest
        ports:
        - containerPort: 80
        env:
        - name: MAX_WORKERS
          value: "4"
        - name: UPLOAD_FILE_SIZE_LIMIT
          value: "10485760"
        volumeMounts:
        - name: data-volume
          mountPath: /app/data
      volumes:
      - name: data-volume
        persistentVolumeClaim:
          claimName: data-processing-pvc
2. Создайте файл service.yaml:
apiVersion: v1
kind: Service
metadata:
  name: data-preprocessing-service
spec:
  selector:
    app: data-preprocessing
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP

3. Создайте файл ingress.yaml (если вы используете Ingress для доступа к приложению):
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: data-preprocessing-ingress
spec:
  rules:
  - host: preprocessing.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: data-preprocessing-service
            port:
              number: 80

4. Создайте файл pvc.yaml для хранения данных:
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-processing-pvc
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi

5. Соберите Docker образ и загрузите его в реестр:

docker build -t yourusername/data-preprocessing-constructor:latest .
docker push yourusername/data-preprocessing-constructor:latest

6. Примените манифесты к кластеру:

kubectl apply -f pvc.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml

Технологический стек

Frontend: Vue.js 3, Element Plus
Backend: Python 3.11, FastAPI
Обработка данных: pandas, numpy, scikit-learn, statsmodels
Инфраструктура: Docker, Nginx

Примеры использования
Приложение может быть полезным для:

Подготовки данных для задач машинного обучения
Предобработки временных рядов перед прогнозированием
Стандартизации и нормализации данных
Обработки категориальных переменных
Выявления и удаления выбросов
Заполнения пропущенных значений
