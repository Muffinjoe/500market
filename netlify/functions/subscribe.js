// Netlify Function: Add email to Resend audience
exports.handler = async (event) => {
    const headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Content-Type": "application/json",
    };

    if (event.httpMethod === "OPTIONS") {
        return { statusCode: 200, headers, body: "" };
    }

    if (event.httpMethod !== "POST") {
        return { statusCode: 405, headers, body: JSON.stringify({ error: "Method not allowed" }) };
    }

    const RESEND_API_KEY = process.env.RESEND_API_KEY;
    const AUDIENCE_ID = "14fe5f34-8795-40c8-8abe-7e32c084b211";

    if (!RESEND_API_KEY) {
        return { statusCode: 500, headers, body: JSON.stringify({ error: "API key not configured" }) };
    }

    let email, firstName;
    try {
        const body = JSON.parse(event.body);
        email = body.email;
        firstName = body.firstName || "";
    } catch {
        return { statusCode: 400, headers, body: JSON.stringify({ error: "Invalid request body" }) };
    }

    if (!email || !email.includes("@")) {
        return { statusCode: 400, headers, body: JSON.stringify({ error: "Valid email required" }) };
    }

    try {
        const res = await fetch(`https://api.resend.com/audiences/${AUDIENCE_ID}/contacts`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${RESEND_API_KEY}`,
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                email,
                first_name: firstName,
                unsubscribed: false,
            }),
        });

        const data = await res.json();

        if (res.ok) {
            return { statusCode: 200, headers, body: JSON.stringify({ success: true, message: "Subscribed!" }) };
        } else {
            return { statusCode: 400, headers, body: JSON.stringify({ error: data.message || "Failed to subscribe" }) };
        }
    } catch (err) {
        return { statusCode: 500, headers, body: JSON.stringify({ error: "Server error" }) };
    }
};
