package accounts

import (
	"crypto/tls"
	"fmt"
	"net"
	"net/mail"
	"net/smtp"
	"strings"
	"time"

	"github.com/brunoavila55/tucano/internal/platform/config"
)

type Mailer interface {
	Enabled() bool
	SendVerification(email, token string) error
	SendPasswordReset(email, token string) error
}

type SMTPMailer struct {
	config config.SMTPConfig
	origin string
}

func NewSMTPMailer(cfg config.SMTPConfig, origin string) *SMTPMailer {
	return &SMTPMailer{config: cfg, origin: strings.TrimRight(origin, "/")}
}

func (m *SMTPMailer) Enabled() bool { return m.config.Enabled() }

func (m *SMTPMailer) SendVerification(email, token string) error {
	link := m.origin + "/verificar-email?token=" + token
	return m.send(email, "Confirme seu e-mail no Tucano", "Confirme seu e-mail acessando:\r\n\r\n"+link+"\r\n\r\nO link expira em 24 horas.")
}

func (m *SMTPMailer) SendPasswordReset(email, token string) error {
	link := m.origin + "/redefinir-senha?token=" + token
	return m.send(email, "Redefina sua senha do Tucano", "Redefina sua senha acessando:\r\n\r\n"+link+"\r\n\r\nO link expira em 30 minutos. Se você não pediu isso, ignore esta mensagem.")
}

func (m *SMTPMailer) send(recipient, subject, body string) error {
	if !m.Enabled() {
		return nil
	}
	from, err := mail.ParseAddress(m.config.From)
	if err != nil {
		return fmt.Errorf("invalid SMTP_FROM: %w", err)
	}
	to, err := mail.ParseAddress(recipient)
	if err != nil {
		return fmt.Errorf("invalid recipient: %w", err)
	}
	address := net.JoinHostPort(m.config.Host, m.config.Port)
	connection, err := net.DialTimeout("tcp", address, 10*time.Second)
	if err != nil {
		return fmt.Errorf("connect SMTP: %w", err)
	}
	defer func() { _ = connection.Close() }()
	_ = connection.SetDeadline(time.Now().Add(20 * time.Second))

	client, err := smtp.NewClient(connection, m.config.Host)
	if err != nil {
		return fmt.Errorf("create SMTP client: %w", err)
	}
	defer func() { _ = client.Close() }()
	if ok, _ := client.Extension("STARTTLS"); !ok {
		return errorsNoSTARTTLS
	}
	if err := client.StartTLS(&tls.Config{ServerName: m.config.Host, MinVersion: tls.VersionTLS12}); err != nil {
		return fmt.Errorf("start SMTP TLS: %w", err)
	}
	if m.config.Username != "" {
		if err := client.Auth(smtp.PlainAuth("", m.config.Username, m.config.Password, m.config.Host)); err != nil {
			return fmt.Errorf("authenticate SMTP: %w", err)
		}
	}
	if err := client.Mail(from.Address); err != nil {
		return fmt.Errorf("set SMTP sender: %w", err)
	}
	if err := client.Rcpt(to.Address); err != nil {
		return fmt.Errorf("set SMTP recipient: %w", err)
	}
	writer, err := client.Data()
	if err != nil {
		return fmt.Errorf("open SMTP body: %w", err)
	}
	message := "From: " + from.String() + "\r\nTo: " + to.String() + "\r\nSubject: " + subject + "\r\nMIME-Version: 1.0\r\nContent-Type: text/plain; charset=UTF-8\r\n\r\n" + body
	if _, err := writer.Write([]byte(message)); err != nil {
		return fmt.Errorf("write SMTP body: %w", err)
	}
	if err := writer.Close(); err != nil {
		return fmt.Errorf("close SMTP body: %w", err)
	}
	if err := client.Quit(); err != nil {
		return fmt.Errorf("finish SMTP delivery: %w", err)
	}
	return nil
}

var errorsNoSTARTTLS = fmt.Errorf("SMTP server does not advertise STARTTLS")
