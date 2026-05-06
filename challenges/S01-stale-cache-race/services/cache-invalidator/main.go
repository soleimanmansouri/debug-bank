// S01: Cache Invalidator
//
// Subscribes to the price_events fanout exchange on RabbitMQ.
// On receiving a price.updated event, deletes the Redis key price:{product_id}.
//
// This is the correct invalidation path. The race condition is NOT here —
// it is in the API Gateway's read-through fill, which can re-populate Redis
// with stale replica data AFTER this delete runs.
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"time"

	amqp "github.com/rabbitmq/amqp091-go"
	"github.com/redis/go-redis/v9"
)

type PriceEvent struct {
	ProductID string  `json:"product_id"`
	Price     float64 `json:"price"`
	Version   int64   `json:"version"`
}

func redisClient() *redis.Client {
	addr := os.Getenv("REDIS_URL")
	if addr == "" {
		addr = "localhost:6379"
	}
	return redis.NewClient(&redis.Options{Addr: addr})
}

func connectRabbitMQ(url string) (*amqp.Connection, *amqp.Channel, error) {
	conn, err := amqp.Dial(url)
	if err != nil {
		return nil, nil, fmt.Errorf("dial: %w", err)
	}
	ch, err := conn.Channel()
	if err != nil {
		conn.Close()
		return nil, nil, fmt.Errorf("channel: %w", err)
	}
	return conn, ch, nil
}

func main() {
	rabbitURL := os.Getenv("RABBITMQ_URL")
	if rabbitURL == "" {
		rabbitURL = "amqp://guest:guest@localhost:5672/"
	}

	rdb := redisClient()
	ctx := context.Background()

	// Verify Redis connectivity
	if err := rdb.Ping(ctx).Err(); err != nil {
		log.Fatalf("Cannot reach Redis: %v", err)
	}
	log.Println("Connected to Redis")

	// Retry RabbitMQ connection on startup
	var conn *amqp.Connection
	var ch *amqp.Channel
	for i := range 10 {
		var err error
		conn, ch, err = connectRabbitMQ(rabbitURL)
		if err == nil {
			break
		}
		log.Printf("RabbitMQ connect attempt %d failed: %v — retrying in 3s", i+1, err)
		time.Sleep(3 * time.Second)
	}
	if conn == nil {
		log.Fatal("Could not connect to RabbitMQ after 10 attempts")
	}
	defer conn.Close()
	defer ch.Close()
	log.Println("Connected to RabbitMQ")

	// Declare exchange and bind a queue
	if err := ch.ExchangeDeclare("price_events", "fanout", true, false, false, false, nil); err != nil {
		log.Fatalf("exchange declare: %v", err)
	}
	q, err := ch.QueueDeclare("cache-invalidator", true, false, false, false, nil)
	if err != nil {
		log.Fatalf("queue declare: %v", err)
	}
	if err := ch.QueueBind(q.Name, "", "price_events", false, nil); err != nil {
		log.Fatalf("queue bind: %v", err)
	}

	msgs, err := ch.Consume(q.Name, "", false, false, false, false, nil)
	if err != nil {
		log.Fatalf("consume: %v", err)
	}

	log.Println("Cache Invalidator ready — waiting for price.updated events")

	for msg := range msgs {
		var event PriceEvent
		if err := json.Unmarshal(msg.Body, &event); err != nil {
			log.Printf("bad message: %v", err)
			msg.Nack(false, false)
			continue
		}

		key := fmt.Sprintf("price:%s", event.ProductID)
		deleted, err := rdb.Del(ctx, key).Result()
		if err != nil {
			log.Printf("Redis DEL %s failed: %v", key, err)
			msg.Nack(false, true) // requeue
			continue
		}

		if deleted > 0 {
			log.Printf("Invalidated %s (version=%d price=%.2f)", key, event.Version, event.Price)
		} else {
			log.Printf("DEL %s — key was already absent (no-op)", key)
		}

		msg.Ack(false)
	}
}
