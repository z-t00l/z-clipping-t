package com.zubibrand.cliptool;

import android.app.Activity;
import android.os.Bundle;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

// Zubi AI Clipping Tool APK (MVP)
// Ye APK tool ki web UI ko phone par chalata hai: link, clips quantity (1..jitni chahiye),
// language (auto / har language), face tracking / blur, auto emoji.
// Asli video processing phone par heavy hai, is liye wo free GitHub Actions
// (Make Clips workflow) ya Muse computer par hoti hai. UI se job save/share hoti hai.
public class MainActivity extends Activity {
    private WebView webView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        webView = new WebView(this);
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        webView.setWebViewClient(new WebViewClient());
        // GitHub Actions build ke waqt web/index.html assets mein copy ho jati hai.
        webView.loadUrl("file:///android_asset/index.html");
        setContentView(webView);
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }
}
