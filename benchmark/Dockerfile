FROM maven:3.9-eclipse-temurin-21 AS build

WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline

COPY src ./src
RUN mvn clean package -DskipTests


FROM eclipse-temurin:21-jre

WORKDIR /app

COPY --from=build /app/target/*.jar app.jar
COPY input ./input

CMD sh -c '
  START=$(date +%s%3N);
  java -jar app.jar;
  END=$(date +%s%3N);
  echo "APP_TIME_MS=$((END-START))"
'