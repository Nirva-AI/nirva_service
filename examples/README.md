# Nirva Service API Examples

This directory contains practical examples of how to integrate with the Nirva Service API.

## 📁 Files

- **`client_example.py`** - Complete working example demonstrating all major API features
- **`requirements.txt`** - Python dependencies needed to run the examples
- **`README.md`** - This file

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Ensure Servers Are Running

Make sure all three Nirva Service servers are running:

```bash
# From the main project directory
make run-all
```

### 3. Run the Example

```bash
python client_example.py
```

## 🔧 Customization

### Update Credentials

Edit `client_example.py` and change these lines:

```python
username = "your_actual_username"
password = "your_actual_password"
```

### Change Server URLs

If running on different hosts or ports:

```python
client = NirvaClient(
    base_url="http://your-server:8000",
    chat_url="http://your-server:8200"
)
```

## 📚 What the Example Demonstrates

1. **Authentication** - Login and JWT token management
2. **Transcript Upload** - Upload content for analysis
3. **Analysis Workflow** - Start analysis and monitor progress
4. **Event Retrieval** - Get analyzed events and insights
5. **Incremental Analysis** - Real-time content processing
6. **AI Chat** - Conversational interface

## 🧪 Testing Different Scenarios

### Test with Different Content

Modify the `test_content` variable in the main function:

```python
test_content = """
Your custom transcript content here.
This could be meeting notes, daily activities, etc.
"""
```

### Test Error Handling

Try invalid credentials or network issues to see error handling in action.

## 💡 Integration Tips

- **Production Use**: Add proper logging, retry logic, and error handling
- **Rate Limiting**: Implement appropriate delays between API calls
- **Authentication**: Store tokens securely and refresh when needed
- **Monitoring**: Track API response times and success rates

## 🆘 Troubleshooting

### Common Issues

1. **Connection Refused**: Ensure servers are running with `make run-all`
2. **Authentication Failed**: Check username/password in the script
3. **Analysis Timeout**: Increase `max_wait` parameter for longer processing
4. **Import Errors**: Install dependencies with `pip install -r requirements.txt`

### Debug Mode

Add debug output by modifying the client:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📖 Next Steps

After running the examples:

1. **Read the full documentation**: `../docs/CLIENT_INTEGRATION_GUIDE.md`
2. **Explore the API**: Visit `/docs` endpoints in your browser
3. **Build your own client**: Use the examples as a starting point
4. **Test edge cases**: Try various input formats and error conditions
