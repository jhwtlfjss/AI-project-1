package com.project1.companion;

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.security.cert.X509Certificate;

import javax.net.ssl.HostnameVerifier;
import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLSession;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;

public class MainActivity extends Activity {
    private static final String PREFS = "ai_project_1_client";

    private EditText serverInput;
    private EditText tokenInput;
    private EditText clientInput;
    private CheckBox trustSelfSigned;
    private TextView statusText;
    private TextView chatLog;
    private EditText messageInput;
    private Button sendButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        buildUi();
        loadPrefs();
    }

    private void buildUi() {
        int pad = dp(12);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(pad, pad, pad, pad);
        root.setBackgroundColor(Color.rgb(255, 253, 249));
        setContentView(root);

        TextView title = new TextView(this);
        title.setText("AI Project 1");
        title.setTextSize(22);
        title.setTextColor(Color.rgb(32, 33, 35));
        title.setGravity(Gravity.START);
        root.addView(title, new LinearLayout.LayoutParams(-1, -2));

        statusText = new TextView(this);
        statusText.setText("Not connected");
        statusText.setTextColor(Color.rgb(111, 106, 99));
        statusText.setPadding(0, dp(4), 0, dp(8));
        root.addView(statusText, new LinearLayout.LayoutParams(-1, -2));

        serverInput = singleLineInput("Server, e.g. http://192.168.0.62:8765");
        root.addView(serverInput, new LinearLayout.LayoutParams(-1, -2));

        tokenInput = singleLineInput("Token");
        tokenInput.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        root.addView(tokenInput, new LinearLayout.LayoutParams(-1, -2));

        clientInput = singleLineInput("Client name, e.g. android-phone");
        root.addView(clientInput, new LinearLayout.LayoutParams(-1, -2));

        trustSelfSigned = new CheckBox(this);
        trustSelfSigned.setText("Trust self-signed HTTPS");
        trustSelfSigned.setTextColor(Color.rgb(64, 45, 28));
        root.addView(trustSelfSigned, new LinearLayout.LayoutParams(-1, -2));

        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.HORIZONTAL);
        actions.setGravity(Gravity.END);
        root.addView(actions, new LinearLayout.LayoutParams(-1, -2));

        Button connectButton = new Button(this);
        connectButton.setText("Connect");
        connectButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                connect();
            }
        });
        actions.addView(connectButton);

        Button clearButton = new Button(this);
        clearButton.setText("Clear");
        clearButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                chatLog.setText("");
            }
        });
        actions.addView(clearButton);

        ScrollView scroll = new ScrollView(this);
        chatLog = new TextView(this);
        chatLog.setTextSize(16);
        chatLog.setTextColor(Color.rgb(32, 33, 35));
        chatLog.setPadding(0, dp(8), 0, dp(8));
        chatLog.setTextIsSelectable(true);
        scroll.addView(chatLog, new ScrollView.LayoutParams(-1, -2));
        root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));

        LinearLayout composer = new LinearLayout(this);
        composer.setOrientation(LinearLayout.HORIZONTAL);
        root.addView(composer, new LinearLayout.LayoutParams(-1, -2));

        messageInput = new EditText(this);
        messageInput.setHint("Say something...");
        messageInput.setMinLines(2);
        messageInput.setMaxLines(4);
        messageInput.setGravity(Gravity.TOP | Gravity.START);
        composer.addView(messageInput, new LinearLayout.LayoutParams(0, -2, 1));

        sendButton = new Button(this);
        sendButton.setText("Send");
        sendButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                sendMessage();
            }
        });
        composer.addView(sendButton, new LinearLayout.LayoutParams(-2, -2));
    }

    private EditText singleLineInput(String hint) {
        EditText edit = new EditText(this);
        edit.setHint(hint);
        edit.setSingleLine(true);
        edit.setTextSize(14);
        edit.setPadding(0, dp(4), 0, dp(4));
        return edit;
    }

    private void loadPrefs() {
        SharedPreferences prefs = getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        serverInput.setText(prefs.getString("server", "http://"));
        tokenInput.setText(prefs.getString("token", ""));
        clientInput.setText(prefs.getString("client_id", "android-phone"));
        trustSelfSigned.setChecked(prefs.getBoolean("trust_self_signed", false));
    }

    private void savePrefs() {
        getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit()
                .putString("server", serverInput.getText().toString().trim())
                .putString("token", tokenInput.getText().toString().trim())
                .putString("client_id", clientInput.getText().toString().trim())
                .putBoolean("trust_self_signed", trustSelfSigned.isChecked())
                .apply();
    }

    private void connect() {
        savePrefs();
        statusText.setText("Connecting...");
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    JSONObject status = request("GET", "/api/status", null);
                    final String text = "Connected: ready=" + status.optBoolean("ready")
                            + " knowledge=" + status.optInt("knowledge_entries")
                            + " memory=" + status.optInt("memory_facts");
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            statusText.setText(text);
                        }
                    });
                } catch (final Exception ex) {
                    showError("Connection failed: " + ex.getMessage());
                }
            }
        }).start();
    }

    private void sendMessage() {
        final String message = messageInput.getText().toString().trim();
        if (message.length() == 0) {
            return;
        }
        savePrefs();
        appendChat("我", message);
        messageInput.setText("");
        sendButton.setEnabled(false);
        statusText.setText("Thinking...");
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    JSONObject payload = new JSONObject();
                    payload.put("message", message);
                    JSONObject response = request("POST", "/api/chat", payload);
                    final String reply = response.optString("reply", "...");
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            appendChat("你", reply);
                            statusText.setText("Connected");
                            sendButton.setEnabled(true);
                        }
                    });
                } catch (final Exception ex) {
                    showError("Send failed: " + ex.getMessage());
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            sendButton.setEnabled(true);
                        }
                    });
                }
            }
        }).start();
    }

    private JSONObject request(String method, String path, JSONObject payload) throws Exception {
        String base = serverInput.getText().toString().trim();
        if (base.endsWith("/")) {
            base = base.substring(0, base.length() - 1);
        }
        URL url = new URL(base + path);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        if (conn instanceof HttpsURLConnection && trustSelfSigned.isChecked()) {
            trustSelfSigned((HttpsURLConnection) conn);
        }
        conn.setRequestMethod(method);
        conn.setConnectTimeout(15000);
        conn.setReadTimeout(120000);
        conn.setRequestProperty("Accept", "application/json");
        conn.setRequestProperty("X-Companion-Token", tokenInput.getText().toString().trim());
        conn.setRequestProperty("X-Companion-Client", clientInput.getText().toString().trim());
        if (payload != null) {
            byte[] bytes = payload.toString().getBytes(StandardCharsets.UTF_8);
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            conn.setRequestProperty("Content-Length", String.valueOf(bytes.length));
            OutputStream out = conn.getOutputStream();
            out.write(bytes);
            out.close();
        }

        int code = conn.getResponseCode();
        InputStream stream = code >= 400 ? conn.getErrorStream() : conn.getInputStream();
        String body = readAll(stream);
        conn.disconnect();
        if (code >= 400) {
            throw new IOException("HTTP " + code + ": " + body);
        }
        return new JSONObject(body);
    }

    private static String readAll(InputStream stream) throws IOException {
        if (stream == null) {
            return "";
        }
        BufferedReader reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8));
        StringBuilder builder = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            builder.append(line);
            builder.append('\n');
        }
        reader.close();
        return builder.toString().trim();
    }

    private static void trustSelfSigned(HttpsURLConnection conn) throws Exception {
        TrustManager[] trustAll = new TrustManager[]{
                new X509TrustManager() {
                    @Override
                    public void checkClientTrusted(X509Certificate[] chain, String authType) {
                    }

                    @Override
                    public void checkServerTrusted(X509Certificate[] chain, String authType) {
                    }

                    @Override
                    public X509Certificate[] getAcceptedIssuers() {
                        return new X509Certificate[0];
                    }
                }
        };
        SSLContext context = SSLContext.getInstance("TLS");
        context.init(null, trustAll, new SecureRandom());
        conn.setSSLSocketFactory(context.getSocketFactory());
        conn.setHostnameVerifier(new HostnameVerifier() {
            @Override
            public boolean verify(String hostname, SSLSession session) {
                return true;
            }
        });
    }

    private void appendChat(String speaker, String text) {
        String current = chatLog.getText().toString();
        chatLog.setText(current + speaker + "> " + text + "\n\n");
    }

    private void showError(final String message) {
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                statusText.setText(message);
                appendChat("system", message);
            }
        });
    }

    private int dp(int value) {
        return (int) (value * getResources().getDisplayMetrics().density + 0.5f);
    }
}

