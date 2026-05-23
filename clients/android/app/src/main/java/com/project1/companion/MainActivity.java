package com.project1.companion;

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
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
    private CheckBox liveSearchInput;
    private CheckBox autoLookupInput;
    private Spinner searchEngineInput;
    private EditText customSearchInput;
    private TextView statusText;
    private ScrollView chatScroll;
    private LinearLayout chatContainer;
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
        title.setTypeface(Typeface.DEFAULT_BOLD);
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

        LinearLayout searchPanel = new LinearLayout(this);
        searchPanel.setOrientation(LinearLayout.VERTICAL);
        searchPanel.setPadding(0, dp(6), 0, dp(6));
        root.addView(searchPanel, new LinearLayout.LayoutParams(-1, -2));

        liveSearchInput = new CheckBox(this);
        liveSearchInput.setText("Live web search");
        liveSearchInput.setTextColor(Color.rgb(64, 45, 28));
        searchPanel.addView(liveSearchInput, new LinearLayout.LayoutParams(-1, -2));

        autoLookupInput = new CheckBox(this);
        autoLookupInput.setText("Auto lookup triggers");
        autoLookupInput.setTextColor(Color.rgb(64, 45, 28));
        searchPanel.addView(autoLookupInput, new LinearLayout.LayoutParams(-1, -2));

        searchEngineInput = new Spinner(this);
        ArrayAdapter<String> adapter = new ArrayAdapter<String>(
                this,
                android.R.layout.simple_spinner_item,
                new String[]{"google", "baidu", "custom"}
        );
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        searchEngineInput.setAdapter(adapter);
        searchPanel.addView(searchEngineInput, new LinearLayout.LayoutParams(-1, -2));
        searchEngineInput.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                updateCustomSearchState();
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
            }
        });

        customSearchInput = singleLineInput("Custom search URL, e.g. https://example.com/search?q={query}");
        searchPanel.addView(customSearchInput, new LinearLayout.LayoutParams(-1, -2));

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
                chatContainer.removeAllViews();
            }
        });
        actions.addView(clearButton);

        chatScroll = new ScrollView(this);
        chatContainer = new LinearLayout(this);
        chatContainer.setOrientation(LinearLayout.VERTICAL);
        chatContainer.setPadding(0, dp(8), 0, dp(8));
        chatScroll.addView(chatContainer, new ScrollView.LayoutParams(-1, -2));
        root.addView(chatScroll, new LinearLayout.LayoutParams(-1, 0, 1));

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
        liveSearchInput.setChecked(prefs.getBoolean("search_enabled", true));
        autoLookupInput.setChecked(prefs.getBoolean("search_auto_lookup", true));
        setSpinnerValue(searchEngineInput, prefs.getString("search_engine", "google"));
        customSearchInput.setText(prefs.getString("custom_search_url", ""));
        updateCustomSearchState();
    }

    private void savePrefs() {
        getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit()
                .putString("server", serverInput.getText().toString().trim())
                .putString("token", tokenInput.getText().toString().trim())
                .putString("client_id", clientInput.getText().toString().trim())
                .putBoolean("trust_self_signed", trustSelfSigned.isChecked())
                .putBoolean("search_enabled", liveSearchInput.isChecked())
                .putBoolean("search_auto_lookup", autoLookupInput.isChecked())
                .putString("search_engine", selectedSearchEngine())
                .putString("custom_search_url", customSearchInput.getText().toString().trim())
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
                    JSONObject webSearch = new JSONObject();
                    webSearch.put("enabled", liveSearchInput.isChecked());
                    webSearch.put("auto_lookup", autoLookupInput.isChecked());
                    webSearch.put("search_engine", selectedSearchEngine());
                    webSearch.put("custom_search_url", customSearchInput.getText().toString().trim());
                    payload.put("web_search", webSearch);
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
        boolean mine = "我".equals(speaker);
        boolean system = "system".equals(speaker);
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(mine ? Gravity.END : Gravity.START);
        row.setPadding(0, dp(4), 0, dp(4));

        TextView bubble = new TextView(this);
        bubble.setText(speaker + " · " + text);
        bubble.setTextSize(15);
        bubble.setTextColor(Color.rgb(28, 32, 36));
        bubble.setPadding(dp(12), dp(8), dp(12), dp(8));
        bubble.setMaxWidth(dp(300));
        bubble.setBackground(rounded(mine ? Color.rgb(149, 236, 105) : (system ? Color.rgb(221, 227, 234) : Color.WHITE)));

        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-2, -2);
        params.leftMargin = mine ? dp(48) : 0;
        params.rightMargin = mine ? 0 : dp(48);
        row.addView(bubble, params);
        chatContainer.addView(row, new LinearLayout.LayoutParams(-1, -2));
        chatScroll.post(new Runnable() {
            @Override
            public void run() {
                chatScroll.fullScroll(View.FOCUS_DOWN);
            }
        });
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

    private GradientDrawable rounded(int color) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(color);
        drawable.setCornerRadius(dp(14));
        drawable.setStroke(dp(1), Color.rgb(214, 219, 226));
        return drawable;
    }

    private void updateCustomSearchState() {
        if (customSearchInput == null) {
            return;
        }
        customSearchInput.setEnabled("custom".equals(selectedSearchEngine()));
    }

    private String selectedSearchEngine() {
        Object selected = searchEngineInput.getSelectedItem();
        return selected == null ? "google" : selected.toString();
    }

    private void setSpinnerValue(Spinner spinner, String value) {
        for (int i = 0; i < spinner.getCount(); i++) {
            if (value.equals(spinner.getItemAtPosition(i).toString())) {
                spinner.setSelection(i);
                return;
            }
        }
        spinner.setSelection(0);
    }
}
